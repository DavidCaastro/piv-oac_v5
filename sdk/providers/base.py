"""sdk/providers/base.py — BaseProvider abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderRequest:
    """Unified request envelope sent to any provider."""

    messages: list[dict[str, str]]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.2
    system: str = ""


@dataclass
class ProviderResponse:
    """Unified response from any provider."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    raw: Any = None  # original SDK response object, if needed


class ProviderError(Exception):
    """Raised when a provider call fails after all retries."""


class BaseProvider(ABC):
    """Abstract interface all LLM providers must implement.

    Invariants:
    - No credential is ever stored on the instance after __init__ — use Vault.
    - complete() must be synchronous (SDK is sync-first; async is an extension).
    - No LLM call happens inside sdk/providers/ — base.py carries zero logic.
    """

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Send *request* to the provider and return the response.

        Implementations must:
          1. Read credentials via Vault.get_credential() — never hardcode.
          2. Raise ProviderError on non-retryable failure.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is reachable (Tier 1 check — no LLM)."""
        ...
