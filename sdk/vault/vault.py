"""sdk/vault/vault.py — Vault: injection scan + credential verification (Tier 1)."""

from __future__ import annotations

import os
from pathlib import Path

from sdk.utils.injection import InjectionScanner, ScanResult
from sdk.utils.sha256 import SHA256Verifier


class VaultError(Exception):
    """Raised when Vault rejects an input."""


class Vault:
    """Zero-trust credential and injection gate.

    Responsibilities:
      - scanForInjection(): blocks injected text before any LLM call
      - verify(): confirms a framework asset is unmodified (SHA-256)
      - get_credential(): reads API keys from env vars — never from context
    """

    # Env var names per provider (never hardcoded values)
    _CREDENTIAL_VARS: dict[str, str] = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "ollama": "",  # local — no key required
    }

    @staticmethod
    def scan_for_injection(text: str) -> ScanResult:
        """Scan *text* for injection patterns before any LLM invocation.

        Raises:
            VaultError: If the scan detects a HIGH or MEDIUM threat.
        """
        result = InjectionScanner.scan(text)

        if not result.clean and result.threat_level in ("HIGH", "MEDIUM"):
            patterns = {m.pattern_name for m in result.matches}
            raise VaultError(
                f"Injection scan BLOCKED — threat_level={result.threat_level} "
                f"patterns={patterns}"
            )

        return result

    @staticmethod
    def verify(name: str, manifest_path: Path) -> str:
        """Verify a framework asset (skill, contract) against its SHA-256 manifest entry.

        Returns the verified hex digest.
        Raises SHA256VerificationError on mismatch.
        """
        return SHA256Verifier.verify(name, manifest_path)

    @staticmethod
    def get_credential(provider: str) -> str:
        """Read the API key for *provider* from environment variables.

        Returns:
            The credential string (may be empty for local providers like ollama).

        Raises:
            VaultError: If the required env var is missing or empty.
        """
        if provider not in Vault._CREDENTIAL_VARS:
            raise VaultError(f"Unknown provider: '{provider}'")

        env_var = Vault._CREDENTIAL_VARS[provider]

        if not env_var:
            # Local provider — no credential needed
            return ""

        value = os.environ.get(env_var, "")

        if not value:
            raise VaultError(
                f"Credential for provider '{provider}' not found. "
                f"Set env var: {env_var}"
            )

        return value
