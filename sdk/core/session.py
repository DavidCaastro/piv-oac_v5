"""sdk/core/session.py — SessionManager: .piv/ state management + checkpoint protocol."""

from __future__ import annotations

import json
import uuid
from datetime import timezone, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class SessionStatus(str, Enum):
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"
    PAUSED    = "paused"


class CheckpointType(str, Enum):
    PHASE_START  = "phase_start"
    PHASE_END    = "phase_end"
    GATE_VERDICT = "gate_verdict"
    AGENT_LOG    = "agent_log"
    ERROR        = "error"


class SessionError(Exception):
    """Raised on invalid session state transitions."""


class SessionManager:
    """.piv/ session state reader/writer.

    State layout (_context_.md §15):
        .piv/
        ├── active/<session_id>.json        ← running sessions
        ├── completed/<session_id>.json     ← gracefully closed sessions
        ├── failed/<session_id>.json        ← circuit-breaker or crash sessions
        └── checkpoints/<session_id>.jsonl  ← append-only checkpoint log

    All state files are JSON (machine-written, universally parseable).
    The TelemetryLogger is the sole writer to logs/ — SessionManager writes only .piv/.
    """

    def __init__(self, repo_root: Path) -> None:
        self._piv = repo_root / ".piv"
        self._active     = self._piv / "active"
        self._completed  = self._piv / "completed"
        self._failed     = self._piv / "failed"
        self._checkpoints = self._piv / "checkpoints"

        for d in (self._active, self._completed, self._failed, self._checkpoints):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create(self, objective: str, provider: str) -> dict[str, Any]:
        """Create and persist a new session record.

        Returns:
            The session state dict (includes generated session_id).
        """
        session_id = str(uuid.uuid4())
        now = _now_iso()

        state: dict[str, Any] = {
            "session_id": session_id,
            "status": SessionStatus.ACTIVE,
            "objective": objective,
            "provider": provider,
            "created_at": now,
            "updated_at": now,
            "phase": "PHASE_0",
            "consecutive_rejections": 0,
            "dag": None,
        }

        self._write_state(self._active / f"{session_id}.json", state)
        return state

    def load(self, session_id: str) -> dict[str, Any]:
        """Load an active session by ID."""
        path = self._active / f"{session_id}.json"
        if not path.exists():
            raise SessionError(f"No active session: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, session_id: str, updates: dict[str, Any]) -> None:
        """Apply *updates* to an active session's state."""
        state = self.load(session_id)
        state.update(updates)
        state["updated_at"] = _now_iso()
        self._write_state(self._active / f"{session_id}.json", state)

    def close(self, session_id: str, status: SessionStatus = SessionStatus.COMPLETED) -> None:
        """Move session from active/ to completed/ or failed/."""
        state = self.load(session_id)
        state["status"] = status
        state["closed_at"] = _now_iso()

        dest_dir = self._completed if status == SessionStatus.COMPLETED else self._failed
        dest = dest_dir / f"{session_id}.json"

        self._write_state(dest, state)
        (self._active / f"{session_id}.json").unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Checkpoint protocol
    # ------------------------------------------------------------------

    def checkpoint(
        self,
        session_id: str,
        checkpoint_type: CheckpointType,
        agent_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Append a checkpoint record to .piv/checkpoints/<session_id>.jsonl.

        ExecutionAuditor reads these records during PHASE 5 monitoring.
        """
        record = {
            "timestamp_ms": _now_ms(),
            "session_id": session_id,
            "checkpoint_type": checkpoint_type,
            "agent_id": agent_id,
            "payload": payload,
        }
        cp_file = self._checkpoints / f"{session_id}.jsonl"
        with cp_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
            fh.flush()

    def list_checkpoints(self, session_id: str) -> list[dict[str, Any]]:
        """Return all checkpoint records for *session_id* (in order)."""
        cp_file = self._checkpoints / f"{session_id}.jsonl"
        if not cp_file.exists():
            return []
        return [
            json.loads(line)
            for line in cp_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # ------------------------------------------------------------------
    # Interrupted session detection
    # ------------------------------------------------------------------

    def find_interrupted(self) -> list[dict[str, Any]]:
        """Return all sessions currently in active/ (may be interrupted)."""
        sessions = []
        for path in self._active.glob("*.json"):
            try:
                sessions.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return sessions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_state(path: Path, state: dict[str, Any]) -> None:
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _now_ms() -> int:
    import time
    return int(time.time() * 1000)
