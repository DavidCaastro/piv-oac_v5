"""sdk/agents/base.py — AgentBase: retry + timeout wrapper for LLM provider calls.

Provides a single @staticmethod entry point (AgentBase.call) that applies
retry-with-backoff and per-call timeout around any provider.complete() call.

This is the agent-level defence layer. Provider-level retry (B1.2) targets
network errors; AgentBase targets agent execution errors (timeouts, ProviderError).
They are complementary, not duplicated.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from sdk.exceptions import AgentUnrecoverable
from sdk.providers.base import ProviderError, ProviderRequest, ProviderResponse


@dataclass
class AgentCallResult:
    """Result of a single AgentBase.call() execution."""

    content: str
    input_tokens: int
    output_tokens: int
    model: str
    attempts: int
    duration_ms: int

    @property
    def tokens_used(self) -> int:
        return self.input_tokens + self.output_tokens


class AgentBase:
    """Utility wrapper for LLM agent calls with retry and timeout.

    Usage:
        result = await AgentBase.call(
            provider=provider,
            request=req,
            agent_id="SecurityAgent",
            session_id=session_id,
        )
    """

    @staticmethod
    async def call(
        provider,
        request: ProviderRequest,
        agent_id: str,
        session_id: str,
        timeout_s: float = 120.0,
        max_retries: int = 2,
    ) -> AgentCallResult:
        """Execute a provider LLM call with retry + timeout.

        Retries on asyncio.TimeoutError and ProviderError with exponential backoff.
        Any other exception is wrapped in AgentUnrecoverable and raised immediately.

        Args:
            provider:    Async provider instance (must have .complete(request) method).
            request:     ProviderRequest describing the LLM call.
            agent_id:    Identifier for logging and error messages.
            session_id:  Current session identifier.
            timeout_s:   Per-attempt hard timeout in seconds.
            max_retries: Number of additional attempts after the first failure.

        Returns:
            AgentCallResult with content, token counts, and attempt metadata.

        Raises:
            AgentUnrecoverable: On unretryable error or exhausted attempts.
        """
        start_ms = int(time.time() * 1000)
        last_exc: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp: ProviderResponse = await asyncio.wait_for(
                    provider.complete(request),
                    timeout=timeout_s,
                )
                duration_ms = int(time.time() * 1000) - start_ms
                return AgentCallResult(
                    content=resp.content,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                    model=resp.model,
                    attempts=attempt + 1,
                    duration_ms=duration_ms,
                )
            except (asyncio.TimeoutError, ProviderError) as exc:
                last_exc = exc
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * (2 ** attempt))
            except Exception as exc:
                raise AgentUnrecoverable(
                    f"Agent {agent_id} (session={session_id[:8]}) encountered "
                    f"unrecoverable error: {exc}"
                ) from exc

        raise AgentUnrecoverable(
            f"Agent {agent_id} (session={session_id[:8]}) exhausted "
            f"{max_retries + 1} attempt(s): {last_exc}"
        ) from last_exc
