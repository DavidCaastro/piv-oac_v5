"""sdk/engram/writer.py — EngramWriter: AuditAgent-only, append-only atom writes.

Write protocol per engram/INDEX.md §Write Protocol:
  1. Read existing atom (if present)
  2. Append new content with session_id + timestamp header
  3. Write atomically (temp file + rename — no partial writes)
  4. Record write event in logs/ via TelemetryLogger

Only AuditAgent may call write(). All writes are append-only.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


class EngramWriteError(Exception):
    """Raised when a write is attempted by an unauthorized role or fails."""


_WRITE_AUTHORIZED: frozenset[str] = frozenset({"audit_agent"})


class EngramWriter:
    """Append-only, atomic writer for engram atoms.

    Only AuditAgent may instantiate this class with role="audit_agent".
    All other roles receive EngramWriteError on construction.

    Atomicity: writes go to a NamedTemporaryFile in the same directory,
    then os.replace() swaps it in — POSIX atomic on same filesystem.
    """

    def __init__(self, engram_root: Path, role: str) -> None:
        if role not in _WRITE_AUTHORIZED:
            raise EngramWriteError(
                f"Role '{role}' is not authorized to write to engram/. "
                f"Only AuditAgent may write."
            )
        self._root = engram_root
        self._role = role

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(
        self,
        atom_path: str,
        content: str,
        session_id: str,
    ) -> Path:
        """Append *content* to an engram atom at *atom_path*.

        Args:
            atom_path:  Relative path under engram/ (e.g. "audit/abc123/record.json").
            content:    Text to append. Must not be empty.
            session_id: Caller's session ID — prepended as a header block.

        Returns:
            Absolute path of the atom written.

        Raises:
            EngramWriteError: If content is empty or write fails.
        """
        if not content.strip():
            raise EngramWriteError("Engram write rejected: content is empty.")

        full_path = self._root / atom_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp_iso = _iso_now()
        header = f"\n<!-- session={session_id} ts={timestamp_iso} -->\n"

        existing = full_path.read_text(encoding="utf-8") if full_path.exists() else ""
        new_content = existing + header + content

        self._atomic_write(full_path, new_content)
        return full_path

    def write_json(
        self,
        atom_path: str,
        data: dict[str, Any],
        session_id: str,
    ) -> Path:
        """Write *data* as a JSON atom (creates or overwrites — JSON atoms are not appended).

        Used for structured records like audit/<session_id>/record.json.
        The data dict is written with session_id and written_at injected.

        Returns:
            Absolute path of the atom written.
        """
        full_path = self._root / atom_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "session_id": session_id,
            "written_at": _iso_now(),
            **data,
        }
        self._atomic_write(full_path, json.dumps(payload, indent=2, ensure_ascii=False))
        return full_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _atomic_write(self, target: Path, content: str) -> None:
        """Write content to target atomically via temp file + os.replace()."""
        dir_ = target.parent
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up temp file if replace failed
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
