"""sdk/pmia/broker.py — PMIABroker: sign, validate, log, route inter-agent messages.

Per contracts/_base.md §3:
  - HMAC-SHA256 signature on every message (key from env PIV_PMIA_SECRET,
    falls back to session_id for local dev — logs a warning)
  - AuditAgent logs every message BEFORE it is processed — no exceptions
  - Max 2 retry attempts on malformed/rejected messages, then PROTOCOL_VIOLATION
  - No direct agent-to-agent — all messages pass through this broker

Per contracts/_base.md §4 (Gate Invariants):
  - CROSS_ALERT from SecurityAgent overrides any GATE_VERDICT: APPROVED
    at any gate, at any phase — broker enforces this immediately
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any, Callable

from .messages import (
    EscalationReason,
    MessageType,
    PMIAError,
    PMIAMessage,
    escalation,
    validate_size,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2   # contracts/_base.md §3: max 2 attempts before PROTOCOL_VIOLATION


class PMIABroker:
    """Central message broker for all inter-agent PMIA v5.0 communication.

    Lifecycle:
        Instantiated once per session in AsyncSession.
        Closed at PHASE 8 via broker.close().

    Security:
        HMAC key sourced from PIV_PMIA_SECRET env var.
        Absent key → ephemeral session_id-derived key + WARNING logged.
        Credentials never appear in any message payload or log entry.

    Routing:
        Handlers registered per MessageType via register().
        CROSS_ALERT from SecurityAgent bypasses normal routing and
        sets the session veto flag immediately.
    """

    def __init__(self, session_id: str, telemetry_logger: Any | None = None) -> None:
        self._session_id  = session_id
        self._telemetry   = telemetry_logger
        self._veto_active = False           # set True on SecurityAgent CROSS_ALERT
        self._handlers: dict[MessageType, list[Callable]] = {t: [] for t in MessageType}
        self._retry_counts: dict[str, int] = {}  # agent_id → consecutive failures

        raw_key = os.environ.get("PIV_PMIA_SECRET", "")
        if raw_key:
            self._hmac_key = raw_key.encode()
        else:
            # Dev mode: ephemeral key derived from session_id — NOT production safe
            self._hmac_key = session_id.encode()
            logger.warning(
                "[PMIABroker] PIV_PMIA_SECRET not set — using ephemeral key. "
                "Set the env var before production use."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, msg_type: MessageType, handler: Callable[[PMIAMessage], None]) -> None:
        """Register a handler for a message type. Multiple handlers allowed."""
        self._handlers[msg_type].append(handler)

    @property
    def veto_active(self) -> bool:
        """True if SecurityAgent has issued a CROSS_ALERT this session."""
        return self._veto_active

    def send(self, msg: PMIAMessage) -> PMIAMessage:
        """Sign, validate, log, and route a message.

        Returns the signed message.
        Raises PMIAError if message is malformed after max retries.
        """
        # 1 — validate size (contracts/_base.md §3 hard limit)
        try:
            validate_size(msg)
        except PMIAError as exc:
            return self._handle_retry(msg, str(exc))

        # 2 — sign
        signed = self._sign(msg)

        # 3 — log (AuditAgent responsibility: every message before processing)
        self._audit_log(signed)

        # 4 — CROSS_ALERT veto — overrides everything (contracts/_base.md §4)
        if signed.type == MessageType.CROSS_ALERT:
            self._veto_active = True
            logger.critical(
                "[PMIABroker] CROSS_ALERT received — session veto active. "
                "agent=%s severity=%s",
                signed.agent_id,
                signed.payload.get("severity"),
            )

        # 5 — route to registered handlers
        self._dispatch(signed)

        # 6 — reset retry counter on success
        self._retry_counts.pop(msg.agent_id, None)

        return signed

    def verify(self, msg: PMIAMessage) -> bool:
        """Verify the HMAC-SHA256 signature of a received message."""
        expected = self._compute_hmac(msg)
        return hmac.compare_digest(expected, msg.signature)

    def close(self) -> None:
        """No-op — broker holds no file handles. Exists for lifecycle symmetry."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, msg: PMIAMessage) -> PMIAMessage:
        sig = self._compute_hmac(msg)
        return msg.with_signature(sig)

    def _compute_hmac(self, msg: PMIAMessage) -> str:
        return hmac.new(
            self._hmac_key,
            msg.unsigned_bytes(),
            hashlib.sha256,
        ).hexdigest()

    def _audit_log(self, msg: PMIAMessage) -> None:
        """Write the message to TelemetryLogger as an AuditAgent log entry.

        This is the broker's AuditAgent responsibility:
        every message is logged before handlers process it.
        Credentials are never logged — only message metadata.
        """
        entry = {
            "level":       "INFO",
            "session_id":  self._session_id,
            "agent_id":    "AuditAgent[broker]",
            "phase":       "PMIA",
            "action":      "message_received",
            "outcome":     "OK",
            "tier":        1,
            "duration_ms": 0,
            "tokens_used": 0,
            "detail": {
                "msg_type":    msg.type.value,
                "from_agent":  msg.agent_id,
                "payload_keys": list(msg.payload.keys()),
                "signed":      bool(msg.signature),
            },
        }
        if self._telemetry:
            self._telemetry.record(entry)
        else:
            logger.debug("[PMIABroker] %s from %s", msg.type.value, msg.agent_id)

    def _dispatch(self, msg: PMIAMessage) -> None:
        for handler in self._handlers[msg.type]:
            try:
                handler(msg)
            except Exception as exc:
                logger.error("[PMIABroker] handler error for %s: %s", msg.type.value, exc)

    def _handle_retry(self, msg: PMIAMessage, error: str) -> PMIAMessage:
        """Track retries; escalate as PROTOCOL_VIOLATION after _MAX_RETRIES."""
        count = self._retry_counts.get(msg.agent_id, 0) + 1
        self._retry_counts[msg.agent_id] = count

        if count >= _MAX_RETRIES:
            self._retry_counts.pop(msg.agent_id, None)
            proto_violation = escalation(
                agent_id="PMIABroker",
                session_id=self._session_id,
                reason=EscalationReason.PROTOCOL_VIOLATION,
                context=f"Max retries ({_MAX_RETRIES}) reached for {msg.agent_id}: {error[:100]}",
            )
            signed = self._sign(proto_violation)
            self._audit_log(signed)
            self._dispatch(signed)
            raise PMIAError(
                f"PROTOCOL_VIOLATION escalated after {_MAX_RETRIES} retries: {error}"
            )

        logger.warning(
            "[PMIABroker] retry %d/%d for %s: %s",
            count, _MAX_RETRIES, msg.agent_id, error,
        )
        return msg  # caller may resend
