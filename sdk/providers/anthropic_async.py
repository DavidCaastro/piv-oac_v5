"""sdk/providers/anthropic_async.py — Async Anthropic provider (Tier 3, cloud).

Enables true parallel agent execution via asyncio.gather().
Used by sdk/core/session_async.py for PHASE 5 concurrent specialists.
"""

from __future__ import annotations

import anthropic

from sdk.vault import Vault

from .base import ProviderError, ProviderRequest, ProviderResponse


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
        """Async call to Anthropic Messages API.

        Safe to call concurrently — AsyncAnthropic client is thread/async safe.

        Raises:
            ProviderError: On API error or auth failure.
        """
        try:
            params: dict = {
                "model": request.model or self.model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": request.messages,
            }
            if request.system:
                params["system"] = request.system

            msg = await self._client.messages.create(**params)

            return ProviderResponse(
                content=msg.content[0].text,
                model=msg.model,
                input_tokens=msg.usage.input_tokens,
                output_tokens=msg.usage.output_tokens,
                raw=msg,
            )
        except anthropic.APIError as exc:
            raise ProviderError(f"Anthropic async API error: {exc}") from exc
