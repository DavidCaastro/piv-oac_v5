"""sdk/utils/injection.py — InjectionScanner (Tier 1, compiled regex only, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Pattern groups
# ---------------------------------------------------------------------------

# Prompt injection attempts: classic override phrases
_PROMPT_OVERRIDE = re.compile(
    r"ignore\s+(all\s+)?previous\s+instructions?|"
    r"disregard\s+(all\s+)?prior\s+instructions?|"
    r"forget\s+(everything|all)\s+(you\s+)?(know|were\s+told)|"
    r"you\s+are\s+now\s+a\s+\w+|"
    r"new\s+instructions?:|"
    r"system\s+prompt\s*:",
    re.IGNORECASE,
)

# Credential / secret exfiltration probes
_SECRET_PROBE = re.compile(
    r"\b(api[_\s]?key|access[_\s]?token|secret[_\s]?key|private[_\s]?key|"
    r"password|passwd|bearer\s+\w{16,}|sk-[A-Za-z0-9]{32,})\b",
    re.IGNORECASE,
)

# Shell / command injection
_SHELL_INJECTION = re.compile(
    r";\s*rm\s+-rf|"
    r"\|\s*bash|"
    r"`[^`]{1,200}`|"
    r"\$\([^)]{1,200}\)|"
    r"&&\s*(rm|curl|wget|nc\b|ncat\b)|"
    r">\s*/etc/passwd",
    re.IGNORECASE,
)

# Jailbreak / role override
_JAILBREAK = re.compile(
    r"dan\s+mode|"
    r"developer\s+mode\s+enabled|"
    r"do\s+anything\s+now|"
    r"jailbreak|"
    r"unrestricted\s+mode|"
    r"bypass\s+(safety|filter|restriction)",
    re.IGNORECASE,
)

_ALL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PROMPT_OVERRIDE", _PROMPT_OVERRIDE),
    ("SECRET_PROBE", _SECRET_PROBE),
    ("SHELL_INJECTION", _SHELL_INJECTION),
    ("JAILBREAK", _JAILBREAK),
]


@dataclass
class InjectionMatch:
    pattern_name: str
    matched_text: str
    start: int
    end: int


@dataclass
class ScanResult:
    clean: bool
    matches: list[InjectionMatch] = field(default_factory=list)

    @property
    def threat_level(self) -> str:
        if not self.matches:
            return "NONE"
        categories = {m.pattern_name for m in self.matches}
        if "SHELL_INJECTION" in categories or "JAILBREAK" in categories:
            return "HIGH"
        if "PROMPT_OVERRIDE" in categories:
            return "MEDIUM"
        return "LOW"


class InjectionScanner:
    """Scan text for prompt injection and credential exfiltration attempts.

    All checks use compiled regex — zero LLM calls, Tier 1 only.
    Called by Vault before every LLM invocation.
    """

    @staticmethod
    def scan(text: str) -> ScanResult:
        """Scan *text* for injection patterns.

        Returns a ScanResult. If `clean` is False the caller must not
        pass the text to any LLM provider.
        """
        matches: list[InjectionMatch] = []

        for name, pattern in _ALL_PATTERNS:
            for m in pattern.finditer(text):
                matches.append(
                    InjectionMatch(
                        pattern_name=name,
                        matched_text=m.group()[:100],  # truncate for log safety
                        start=m.start(),
                        end=m.end(),
                    )
                )

        return ScanResult(clean=len(matches) == 0, matches=matches)
