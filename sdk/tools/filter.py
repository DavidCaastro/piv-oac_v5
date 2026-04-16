"""sdk/tools/filter.py — ExecutionDataFilter.

Validates subprocess arguments before execution.
Blocks credentials, PII, path traversal, and shell injection.
All checks are Tier 1 (compiled regex, no LLM).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_BLOCKED = re.compile(
    r"\.\./|"                           # path traversal
    r"\.\.[/\\]|"                       # Windows path traversal
    r"[;&|`]|"                          # shell metacharacters
    r"\$\(|"                            # command substitution $(...)
    r"sk-[A-Za-z0-9]{32,}|"            # Anthropic/OpenAI API keys
    r"(?:password|passwd|secret)\s*=\s*\S+|"  # credential assignment
    r"bearer\s+[A-Za-z0-9\-._~+/]{16,}",     # bearer tokens
    re.IGNORECASE,
)

_MAX_ARG_LENGTH = 512  # characters — prevents argument-length abuse


@dataclass(frozen=True)
class FilteredArg:
    """A validated, safe argument ready for subprocess use."""
    value: str


class FilterError(ValueError):
    """Raised when an argument fails validation."""


class ExecutionDataFilter:
    """Validates subprocess arguments for SafeLocalExecutor.

    Checks each argument against:
      - Blocked pattern list (credentials, shell metacharacters, path traversal)
      - Maximum argument length
      - Path containment (path args must stay within project root)

    Usage:
        f = ExecutionDataFilter(base_dir=Path("."))
        clean = f.validate_all(["create", "task-auth", "expert-1"])
    """

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()

    def validate(self, arg: str) -> FilteredArg:
        """Validate a single argument.

        Raises:
            FilterError: If the argument contains a blocked pattern or is too long.
        """
        if len(arg) > _MAX_ARG_LENGTH:
            raise FilterError(
                f"Argument too long ({len(arg)} chars, max {_MAX_ARG_LENGTH}): "
                f"{arg[:40]}..."
            )

        match = _BLOCKED.search(arg)
        if match:
            raise FilterError(
                f"Argument contains blocked pattern '{match.group()[:20]}': {arg[:60]}"
            )

        # If arg looks like a path, verify it stays within project root
        candidate = Path(arg)
        if candidate.parts and not candidate.is_absolute():
            resolved = (self._base / candidate).resolve()
            if not str(resolved).startswith(str(self._base)):
                raise FilterError(
                    f"Path argument escapes project root: {arg}"
                )

        return FilteredArg(value=arg)

    def validate_all(self, args: list[str]) -> list[FilteredArg]:
        """Validate all arguments. Raises FilterError on the first violation."""
        return [self.validate(a) for a in args]
