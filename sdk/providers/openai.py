"""sdk/providers/openai.py — OpenAI provider (Tier 3, cloud)."""

from __future__ import annotations

import openai

from sdk.vault import Vault

from .base import BaseProvider, ProviderError, ProviderRequest, ProviderResponse


class OpenAIProvider(BaseProvider):
    """Thin wrapper around the OpenAI SDK.

    API key is read from env var OPENAI_API_KEY via Vault — never hardcoded.
    """

    def __init__(self, model: str = "gpt-4o") -> None:
        super().__init__(model)
        self._api_key = Vault.get_credential("openai")
        self._client = openai.OpenAI(api_key=self._api_key)

    def is_available(self) -> bool:
        """Tier 1 check — verifies credential exists, no network call."""
        try:
            Vault.get_credential("openai")
            return True
        except Exception:
            return False

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Call the OpenAI Chat Completions API.

        Raises:
            ProviderError: On API error, auth failure, or network issue.
        """
        messages = list(request.messages)
        if request.system:
            messages = [{"role": "system", "content": request.system}] + messages

        try:
            resp = self._client.chat.completions.create(
                model=request.model or self.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            choice = resp.choices[0]
            usage = resp.usage

            return ProviderResponse(
                content=choice.message.content or "",
                model=resp.model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                raw=resp,
            )
        except openai.APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc
