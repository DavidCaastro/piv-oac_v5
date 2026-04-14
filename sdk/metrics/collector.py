"""sdk/metrics/collector.py — TelemetryLogger: session metrics collector.

Lifecycle:
    Instantiated at Session.init(). Open for the entire session.
    No agent writes logs directly — all log records route here.

Write strategy:
    Primary:   logs/<type>/<session_id>.jsonl  (sync, always, flush after every write)
    Secondary: OTEL Collector on :4317         (async, fire-and-forget, silently skipped if down)
"""

from __future__ import annotations

import json
import socket
import threading
import time
from io import TextIOWrapper
from pathlib import Path
from typing import Any


class TelemetryLogger:
    """Persistent structured log writer for a single PIV/OAC session.

    One instance per (session_id, log_type) pair.
    Default log_type is "sessions"; gate verdicts use "gates"; scores use "scores".
    """

    _OTEL_HOST = "localhost"
    _OTEL_PORT = 4317

    def __init__(
        self,
        session_id: str,
        log_dir: Path,
        log_type: str = "sessions",
    ) -> None:
        self.session_id = session_id
        self._log_type = log_type
        self._log_dir = log_dir
        self._index_path = log_dir / "index.jsonl"

        log_path = log_dir / log_type / f"{session_id}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._file: TextIOWrapper = log_path.open("a", encoding="utf-8")
        self._otel_active: bool = self._check_otel_collector()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, entry: dict[str, Any]) -> None:
        """Write one log entry to disk and optionally to OTEL.

        The caller is responsible for building the entry dict conforming
        to the canonical log line format (see _context_.md §10).
        timestamp_ms and timestamp_iso are injected here if absent.
        """
        if "timestamp_ms" not in entry:
            now_ms = int(time.time() * 1000)
            entry = {
                "timestamp_ms": now_ms,
                "timestamp_iso": _ms_to_iso(now_ms),
                **entry,
            }

        line = json.dumps(entry, ensure_ascii=False)
        self._file.write(line + "\n")
        self._file.flush()  # sync write — no data loss on crash

        if self._otel_active:
            threading.Thread(
                target=self._send_otel_async,
                args=(entry,),
                daemon=True,
            ).start()

    def write_index_entry(self, summary: dict[str, Any]) -> None:
        """Append one summary line to logs/index.jsonl (cross-session index).

        Called once per session at closure — before close().
        The index is the single queryable record of all sessions ever run:
            jq 'select(.status=="failed")' logs/index.jsonl
        """
        if "timestamp_iso" not in summary:
            now_ms = int(time.time() * 1000)
            summary = {"timestamp_iso": _ms_to_iso(now_ms), **summary}
        self._log_dir.mkdir(parents=True, exist_ok=True)
        with self._index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
            fh.flush()

    def close(self) -> None:
        """Close the log file. Called at PHASE 8 session closure."""
        self._file.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_otel_collector(self) -> bool:
        """Tier 1: TCP probe — no HTTP, no LLM."""
        try:
            with socket.create_connection(
                (self._OTEL_HOST, self._OTEL_PORT), timeout=1
            ):
                return True
        except OSError:
            return False

    def _send_otel_async(self, entry: dict[str, Any]) -> None:
        """Fire-and-forget OTEL export. Silently absorbs all errors."""
        try:
            import httpx  # lazy import — OTEL path only

            httpx.post(
                f"http://{self._OTEL_HOST}:{self._OTEL_PORT}/logs",
                json=entry,
                timeout=3.0,
            )
        except Exception:
            pass  # OTEL is always secondary — never block on failure


# ---------------------------------------------------------------------------
# MetricsCollector: convenience façade used by EvaluationAgent
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Wrapper around TelemetryLogger for EvaluationAgent scoring records.

    Writes to logs/scores/<session_id>.jsonl.
    """

    def __init__(self, session_id: str, log_dir: Path) -> None:
        self._logger = TelemetryLogger(
            session_id=session_id, log_dir=log_dir, log_type="scores"
        )

    def record(self, entry: dict[str, Any]) -> None:
        self._logger.record(entry)

    def close(self) -> None:
        self._logger.close()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _ms_to_iso(ms: int) -> str:
    """Convert millisecond epoch to ISO-8601 UTC string."""
    seconds = ms / 1000
    t = time.gmtime(seconds)
    frac = ms % 1000
    return (
        f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}T"
        f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{frac:03d}Z"
    )
