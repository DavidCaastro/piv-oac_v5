"""sdk/pmia — PMIA v5.0 inter-agent message protocol.

Per contracts/_base.md: all inter-agent communication routes through PMIABroker.
No agent sends messages directly to another agent.
"""

from .broker import PMIABroker
from .messages import (
    AlertSeverity,
    EscalationReason,
    GateId,
    MessageType,
    PMIAError,
    PMIAMessage,
    Verdict,
    checkpoint_req,
    cross_alert,
    escalation,
    gate_verdict,
)

__all__ = [
    "PMIABroker",
    "PMIAMessage",
    "PMIAError",
    "MessageType",
    "GateId",
    "Verdict",
    "EscalationReason",
    "AlertSeverity",
    "gate_verdict",
    "escalation",
    "cross_alert",
    "checkpoint_req",
]
