"""sdk/exceptions.py — Typed exception hierarchy for PIV/OAC v5.0.

Provides a common base for cross-module exception handling.
Existing module-level exceptions are NOT modified; they can optionally
inherit from this hierarchy in future iterations.
"""

from __future__ import annotations


class PIVOACError(Exception):
    """Base exception for all PIV/OAC framework errors."""


class AgentUnrecoverable(PIVOACError):
    """Irrecoverable failure during agent execution."""


class GateRejected(PIVOACError):
    """A gate returned REJECTED, blocking the pipeline."""

    def __init__(self, gate: str, rationale: str) -> None:
        self.gate = gate
        self.rationale = rationale
        super().__init__(f"Gate {gate} REJECTED: {rationale}")


class VetoError(PIVOACError):
    """SecurityAgent emitted CROSS_ALERT — session vetoed."""


class MalformedOutput(PIVOACError):
    """Agent produced output that does not match the expected contract format."""

    def __init__(self, agent_id: str, expected: str, got: str = "") -> None:
        self.agent_id = agent_id
        self.expected = expected
        self.got = got
        super().__init__(
            f"Agent {agent_id} produced malformed output. "
            f"Expected: {expected}. Got: {got[:200]!r}"
        )


class CircuitOpen(PIVOACError):
    """Circuit breaker threshold reached — session halted."""

    def __init__(self, threshold: int, agent_id: str = "") -> None:
        self.threshold = threshold
        self.agent_id = agent_id
        detail = f" (agent: {agent_id})" if agent_id else ""
        super().__init__(f"Circuit breaker opened at threshold={threshold}{detail}")


class MessageExpired(PIVOACError):
    """PMIAMessage exceeds TTL — possible replay attack."""


class MessageTampered(PIVOACError):
    """HMAC-SHA256 signature invalid — message may have been tampered."""
