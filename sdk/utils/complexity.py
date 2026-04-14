"""sdk/utils/complexity.py — ComplexityClassifier (Tier 1, heuristic only, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Level = Literal[1, 2]

# Keywords that signal architectural scope → Level 2
_ARCH_KEYWORDS: frozenset[str] = frozenset(
    {
        "authentication",
        "authorization",
        "database",
        "migration",
        "integration",
        "payment",
        "oauth",
        "jwt",
        "security",
        "encryption",
        "architecture",
        "refactor",
        "redesign",
        "multi",
        "parallel",
        "distributed",
        "microservice",
        "event",
        "queue",
        "webhook",
        "stripe",
        "twilio",
        "api",
        "endpoint",
    }
)

# Words that indicate trivial scope → Level 1
_MICRO_KEYWORDS: frozenset[str] = frozenset(
    {
        "typo",
        "rename",
        "comment",
        "docstring",
        "readme",
        "log",
        "logging",
        "format",
        "indent",
        "whitespace",
        "bump version",
        "update version",
    }
)


@dataclass(frozen=True)
class ClassificationResult:
    level: Level
    reason: str
    fast_track: bool  # True → Gate 0, skip interview


class ComplexityClassifier:
    """Heuristic classifier to decide interview activation.

    Level 1 (micro-task):
      - ≤ 2 indicative files in the objective
      - No architectural keywords
      - Micro keywords present, OR objective ≤ 60 chars with no ambiguity signals

    Level 2:
      - Any architectural keyword present
      - Multiple file references
      - Objective is ambiguous (question marks, "or", "maybe")
    """

    _FILE_PATTERN = re.compile(r"[\w/\\]+\.\w{1,6}")
    _AMBIGUITY_PATTERN = re.compile(r"\bor\b|\bmaybe\b|\bcould\b|\?")

    @classmethod
    def classify(cls, objective: str) -> ClassificationResult:
        lower = objective.lower()
        file_refs = cls._FILE_PATTERN.findall(objective)
        has_arch = any(kw in lower for kw in _ARCH_KEYWORDS)
        has_micro = any(kw in lower for kw in _MICRO_KEYWORDS)
        has_ambiguity = bool(cls._AMBIGUITY_PATTERN.search(lower))
        many_files = len(file_refs) > 2

        if has_arch or has_ambiguity or many_files:
            return ClassificationResult(
                level=2,
                reason=(
                    "architectural scope"
                    if has_arch
                    else "ambiguous objective"
                    if has_ambiguity
                    else "multiple file references"
                ),
                fast_track=False,
            )

        if has_micro or (len(objective) <= 80 and not has_ambiguity):
            return ClassificationResult(
                level=1,
                reason="micro-task: unambiguous, narrow scope",
                fast_track=True,
            )

        # Default conservative: treat as Level 2
        return ClassificationResult(
            level=2,
            reason="scope unclear — defaulting to interview",
            fast_track=False,
        )
