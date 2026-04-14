"""sdk/pmia/messages.py — PMIA v5.0 message types and validation.

Four message types per contracts/_base.md:
  GATE_VERDICT    → gate agent → MasterOrchestrator
  ESCALATION      → any agent → level above
  CROSS_ALERT     → SecurityAgent → any
  CHECKPOINT_REQ  → any agent → AuditAgent

Hard constraints (non-overridable per contracts/_base.md §3):
  - Max 300 tokens per message (~1 200 chars, conservative estimate)
  - No secrets in any field
  - All fields required except rationale/context (max 200 tokens each)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_MAX_MSG_CHARS  = 1_200   # ≈ 300 tokens (4 chars/token conservative)
_MAX_TEXT_CHARS = 800     # ≈ 200 tokens for rationale/context fields


class MessageType(str, Enum):
    GATE_VERDICT    = "GATE_VERDICT"
    ESCALATION      = "ESCALATION"
    CROSS_ALERT     = "CROSS_ALERT"
    CHECKPOINT_REQ  = "CHECKPOINT_REQ"


class GateId(str, Enum):
    GATE_0  = "Gate0"
    GATE_1  = "Gate1"
    GATE_2  = "Gate2"
    GATE_2B = "Gate2b"
    GATE_3  = "Gate3"


class Verdict(str, Enum):
    APPROVED       = "APPROVED"
    REJECTED       = "REJECTED"
    BLOCKED_BY_TOOL = "BLOCKED_BY_TOOL"


class EscalationReason(str, Enum):
    CONTEXT_SATURATION   = "CONTEXT_SATURATION"
    UNRESOLVABLE_CONFLICT = "UNRESOLVABLE_CONFLICT"
    PROTOCOL_VIOLATION   = "PROTOCOL_VIOLATION"


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"


class PMIAError(ValueError):
    """Raised when a message fails validation."""


@dataclass(frozen=True)
class PMIAMessage:
    """A validated, signable PMIA v5.0 inter-agent message."""

    type:         MessageType
    agent_id:     str
    session_id:   str
    payload:      dict[str, Any]
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    signature:    str = ""          # filled by PMIABroker.send()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type":         self.type.value,
            "agent_id":     self.agent_id,
            "session_id":   self.session_id,
            "payload":      self.payload,
            "timestamp_ms": self.timestamp_ms,
            "signature":    self.signature,
        }

    def unsigned_bytes(self) -> bytes:
        """Canonical bytes for HMAC signing (excludes signature field)."""
        import json
        d = self.to_dict()
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, ensure_ascii=False).encode()

    def with_signature(self, sig: str) -> "PMIAMessage":
        return PMIAMessage(
            type=self.type,
            agent_id=self.agent_id,
            session_id=self.session_id,
            payload=self.payload,
            timestamp_ms=self.timestamp_ms,
            signature=sig,
        )


# ---------------------------------------------------------------------------
# Factory functions — enforce field constraints at construction time
# ---------------------------------------------------------------------------

def gate_verdict(
    agent_id: str,
    session_id: str,
    gate: GateId,
    verdict: Verdict,
    rationale: str,
) -> PMIAMessage:
    _check_text(rationale, "rationale")
    return PMIAMessage(
        type=MessageType.GATE_VERDICT,
        agent_id=agent_id,
        session_id=session_id,
        payload={
            "gate":      gate.value,
            "verdict":   verdict.value,
            "rationale": rationale,
        },
    )


def escalation(
    agent_id: str,
    session_id: str,
    reason: EscalationReason,
    context: str,
) -> PMIAMessage:
    _check_text(context, "context")
    return PMIAMessage(
        type=MessageType.ESCALATION,
        agent_id=agent_id,
        session_id=session_id,
        payload={
            "reason":  reason.value,
            "context": context,
        },
    )


def cross_alert(
    agent_id: str,
    session_id: str,
    severity: AlertSeverity,
    description: str,
    action_required: str,
) -> PMIAMessage:
    if agent_id != "SecurityAgent":
        raise PMIAError("CROSS_ALERT may only be issued by SecurityAgent")
    _check_text(description,    "description")
    _check_text(action_required, "action_required")
    return PMIAMessage(
        type=MessageType.CROSS_ALERT,
        agent_id=agent_id,
        session_id=session_id,
        payload={
            "severity":        severity.value,
            "description":     description,
            "action_required": action_required,
        },
    )


def checkpoint_req(
    agent_id: str,
    session_id: str,
    phase: str,
    state_summary: str,
) -> PMIAMessage:
    _check_text(state_summary, "state_summary")
    return PMIAMessage(
        type=MessageType.CHECKPOINT_REQ,
        agent_id=agent_id,
        session_id=session_id,
        payload={
            "phase":         phase,
            "state_summary": state_summary,
        },
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _check_text(text: str, field_name: str) -> None:
    if len(text) > _MAX_TEXT_CHARS:
        raise PMIAError(
            f"Field '{field_name}' exceeds ~200 token limit "
            f"({len(text)} chars, max {_MAX_TEXT_CHARS})"
        )


def validate_size(msg: PMIAMessage) -> None:
    """Raise PMIAError if the full message exceeds the 300-token hard limit."""
    import json
    size = len(json.dumps(msg.to_dict(), ensure_ascii=False))
    if size > _MAX_MSG_CHARS:
        raise PMIAError(
            f"Message exceeds 300-token limit ({size} chars, max {_MAX_MSG_CHARS})"
        )
