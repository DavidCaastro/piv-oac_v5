"""sdk/providers/anthropic_async.py — Async Anthropic provider (Tier 3, cloud).

Enables true parallel agent execution via asyncio.gather().
Used by sdk/core/session_async.py for PHASE 5 concurrent specialists.
"""

from __future__ import annotations

import asyncio

import anthropic

from sdk.vault import Vault

from .base import ProviderError, ProviderRequest, ProviderResponse

_TIMEOUT_S    = 120.0
_MAX_RETRIES  = 3
_BASE_DELAY_S = 1.0
_RETRYABLE    = (429, 500, 502, 503, 529)


class AsyncAnthropicProvider:
    """Async wrapper around the Anthropic SDK.

    Designed for concurrent use: each call is independent and awaitable.
    Multiple agents call complete() simultaneously via asyncio.gather().
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self.model = model
        self._api_key = Vault.get_credential("anthropic")
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    def is_available(self) -> bool:
        """Tier 1 check — credential exists, no network call."""
        try:
            Vault.get_credential("anthropic")
            return True
        except Exception:
            return False

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Async call to Anthropic Messages API with retry + timeout.

        Retries on network errors, 429, and 5xx responses with exponential backoff.
        Hard timeout of 120s per attempt.

        Raises:
            ProviderError: On unretryable error or exhausted retries.
        """
        params: dict = {
            "model": request.model or self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
        }
        if request.system:
            params["system"] = request.system

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                msg = await asyncio.wait_for(
                    self._client.messages.create(**params),
                    timeout=_TIMEOUT_S,
                )
                return ProviderResponse(
                    content=msg.content[0].text,
                    model=msg.model,
                    input_tokens=msg.usage.input_tokens,
                    output_tokens=msg.usage.output_tokens,
                    raw=msg,
                )
            except asyncio.TimeoutError as exc:
                last_exc = exc
                await asyncio.sleep(_BASE_DELAY_S * (2 ** attempt))
            except anthropic.RateLimitError as exc:
                last_exc = exc
                await asyncio.sleep(_BASE_DELAY_S * (2 ** attempt))
            except anthropic.APIStatusError as exc:
                if exc.status_code in _RETRYABLE:
                    last_exc = exc
                    await asyncio.sleep(_BASE_DELAY_S * (2 ** attempt))
                else:
                    raise ProviderError(f"Anthropic async API error: {exc}") from exc
            except anthropic.APIError as exc:
                raise ProviderError(f"Anthropic async API error: {exc}") from exc

        raise ProviderError(
            f"Anthropic provider exhausted {_MAX_RETRIES} retries: {last_exc}"
        ) from last_exc
