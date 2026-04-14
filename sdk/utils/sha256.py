"""sdk/utils/sha256.py — SHA-256 file verification (Tier 1, no LLM)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class SHA256VerificationError(Exception):
    """Raised when a file hash does not match the manifest entry."""


class SHA256Verifier:
    """Verify files against a SHA-256 manifest.

    All operations are local and deterministic — no LLM, no network.
    """

    @staticmethod
    def hash_file(file_path: Path) -> str:
        """Return the SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify(name: str, manifest_path: Path) -> str:
        """Verify *name* against the manifest at *manifest_path*.

        Args:
            name: Key in the manifest (usually a skill name, no extension).
            manifest_path: Path to the JSON manifest containing {name: sha256}.

        Returns:
            The verified hex digest.

        Raises:
            FileNotFoundError: If the manifest or the target file is missing.
            SHA256VerificationError: If the hash does not match.
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        manifest: dict[str, str] = json.loads(manifest_path.read_text(encoding="utf-8"))

        if name not in manifest:
            raise SHA256VerificationError(
                f"'{name}' not found in manifest {manifest_path}"
            )

        expected: str = manifest[name]
        target = manifest_path.parent / f"{name}.md"

        if not target.exists():
            raise FileNotFoundError(f"Target file not found: {target}")

        actual = SHA256Verifier.hash_file(target)

        if actual != expected:
            raise SHA256VerificationError(
                f"Hash mismatch for '{name}': expected {expected[:12]}… got {actual[:12]}…"
            )

        return actual
