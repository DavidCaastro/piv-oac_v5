"""sdk/providers/ollama.py — Ollama provider (Tier 2, local inference)."""

from __future__ import annotations

import json
import socket

import httpx

from .base import BaseProvider, ProviderError, ProviderRequest, ProviderResponse

_DEFAULT_HOST = "http://localhost:11434"
_TIMEOUT = 120.0  # seconds — local inference can be slow on limited hardware


class OllamaProvider(BaseProvider):
    """Ollama local inference provider.

    No credentials required — runs on localhost.
    Falls back gracefully: if Ollama is unreachable, the router selects Tier 3.
    """

    def __init__(self, model: str = "llama3.2:1b", host: str = _DEFAULT_HOST) -> None:
        super().__init__(model)
        self._host = host.rstrip("/")

    def is_available(self) -> bool:
        """Tier 1 check — TCP probe to Ollama host, no HTTP overhead."""
        try:
            parts = self._host.replace("http://", "").replace("https://", "").split(":")
            hostname = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 11434
            with socket.create_connection((hostname, port), timeout=2):
                return True
        except OSError:
            return False

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Call Ollama /api/chat endpoint.

        Raises:
            ProviderError: If Ollama is unreachable or returns an error.
        """
        messages = list(request.messages)
        if request.system:
            messages = [{"role": "system", "content": request.system}] + messages

        payload = {
            "model": request.model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{self._host}/api/chat", json=payload)
                resp.raise_for_status()

            data = resp.json()
            content = data.get("message", {}).get("content", "")
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)

            return ProviderResponse(
                content=content,
                model=data.get("model", request.model or self.model),
                input_tokens=prompt_eval_count,
                output_tokens=eval_count,
                raw=data,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise ProviderError(f"Ollama response parse error: {exc}") from exc
