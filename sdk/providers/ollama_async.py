"""sdk/providers/ollama_async.py — Async Ollama provider (Tier 2, local inference).

Enables concurrent local inference for L1.5/L2 agents when local_model is set.
Falls back to AsyncAnthropicProvider if Ollama is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import socket

import httpx

from .base import ProviderError, ProviderRequest, ProviderResponse

_DEFAULT_HOST = "http://localhost:11434"
_TIMEOUT      = 120.0
_MAX_RETRIES  = 3
_BASE_DELAY_S = 1.0
_RETRYABLE_ERRORS = (httpx.ConnectError, httpx.RemoteProtocolError)


class AsyncOllamaProvider:
    """Async Ollama local inference provider.

    Uses httpx.AsyncClient for true non-blocking concurrent calls.
    """

    def __init__(self, model: str = "llama3.2:1b", host: str = _DEFAULT_HOST) -> None:
        self.model = model
        self._host = host.rstrip("/")

    def is_available(self) -> bool:
        """Tier 1 TCP probe — sync, called once at session init."""
        try:
            parts = self._host.replace("http://", "").replace("https://", "").split(":")
            hostname = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 11434
            with socket.create_connection((hostname, port), timeout=2):
                return True
        except OSError:
            return False

    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Async call to Ollama /api/chat endpoint with retry on connection errors.

        Retries on ConnectError and RemoteProtocolError with exponential backoff.

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

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(f"{self._host}/api/chat", json=payload)
                    resp.raise_for_status()

                data = resp.json()
                content = data.get("message", {}).get("content", "")

                return ProviderResponse(
                    content=content,
                    model=data.get("model", request.model or self.model),
                    input_tokens=data.get("prompt_eval_count", 0),
                    output_tokens=data.get("eval_count", 0),
                    raw=data,
                )
            except _RETRYABLE_ERRORS as exc:
                last_exc = exc
                await asyncio.sleep(_BASE_DELAY_S * (2 ** attempt))
            except httpx.HTTPError as exc:
                raise ProviderError(f"Ollama async request failed: {exc}") from exc
            except (json.JSONDecodeError, KeyError) as exc:
                raise ProviderError(f"Ollama async response parse error: {exc}") from exc

        raise ProviderError(
            f"Ollama provider exhausted {_MAX_RETRIES} retries: {last_exc}"
        ) from last_exc
