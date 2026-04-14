"""sdk/providers/anthropic.py — Anthropic provider (Tier 3, cloud)."""

from __future__ import annotations

import anthropic

from sdk.vault import Vault

from .base import BaseProvider, ProviderError, ProviderRequest, ProviderResponse


class AnthropicProvider(BaseProvider):
    """Thin wrapper around the Anthropic SDK.

    API key is read from env var ANTHROPIC_API_KEY via Vault — never hardcoded.
    No retry logic here — retries are the caller's responsibility.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        super().__init__(model)
        self._api_key = Vault.get_credential("anthropic")
        self._client = anthropic.Anthropic(api_key=self._api_key)

    def is_available(self) -> bool:
        """Tier 1 check — verifies credential exists, no network call."""
        try:
            Vault.get_credential("anthropic")
            return True
        except Exception:
            return False

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Call the Anthropic Messages API.

        Raises:
            ProviderError: On API error, auth failure, or network issue.
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

            msg = self._client.messages.create(**params)

            return ProviderResponse(
                content=msg.content[0].text,
                model=msg.model,
                input_tokens=msg.usage.input_tokens,
                output_tokens=msg.usage.output_tokens,
                raw=msg,
            )
        except anthropic.APIError as exc:
            raise ProviderError(f"Anthropic API error: {exc}") from exc
