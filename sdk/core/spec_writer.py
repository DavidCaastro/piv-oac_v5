"""sdk/core/spec_writer.py — PHASE 0.2: interview answers → specs/active/."""

from __future__ import annotations

import textwrap
from pathlib import Path


class SpecWriterError(Exception):
    """Raised when spec content is missing required fields."""


class SpecWriter:
    """Converts PHASE 0.1 interview answers into formal spec files.

    Output files (specs/active/):
        functional.md    — what the system must do (always written)
        architecture.md  — structural decisions (Level 2 complex only)
        quality.md       — acceptance criteria and coverage thresholds

    Invariant: DAG is not built and no agents are instantiated until
    the user confirms the specs written here.
    """

    REQUIRED_FUNCTIONAL_KEYS: frozenset[str] = frozenset(
        {"objective", "scope", "acceptance_criteria"}
    )

    def __init__(self, specs_dir: Path) -> None:
        self._specs = specs_dir
        self._active = specs_dir / "active"
        self._active.mkdir(parents=True, exist_ok=True)

    def write_functional(self, data: dict) -> Path:
        """Write specs/active/functional.md from *data*.

        Required keys: objective, scope, acceptance_criteria.
        Optional: constraints, out_of_scope.
        """
        missing = self.REQUIRED_FUNCTIONAL_KEYS - set(data.keys())
        if missing:
            raise SpecWriterError(
                f"functional.md requires: {sorted(missing)}"
            )

        lines = [
            "# Functional Requirements",
            "",
            "## Objective",
            "",
            data["objective"],
            "",
            "## Scope",
            "",
            _bullet_list(data["scope"]),
            "",
            "## Acceptance Criteria",
            "",
            _numbered_list(data["acceptance_criteria"]),
        ]

        if data.get("constraints"):
            lines += ["", "## Constraints", "", _bullet_list(data["constraints"])]

        if data.get("out_of_scope"):
            lines += ["", "## Out of Scope", "", _bullet_list(data["out_of_scope"])]

        return self._write("functional.md", "\n".join(lines))

    def write_architecture(self, data: dict) -> Path:
        """Write specs/active/architecture.md (Level 2 complex only)."""
        lines = [
            "# Architecture Decisions",
            "",
        ]

        for section, content in data.items():
            title = section.replace("_", " ").title()
            lines += [f"## {title}", "", _bullet_list(content) if isinstance(content, list) else str(content), ""]

        return self._write("architecture.md", "\n".join(lines))

    def write_quality(self, data: dict) -> Path:
        """Write specs/active/quality.md."""
        lines = [
            "# Quality Criteria",
            "",
            f"## Coverage Threshold",
            "",
            f"- Minimum: {data.get('coverage_threshold', '80')}%",
            "",
            "## Acceptance Checks",
            "",
            _numbered_list(data.get("acceptance_checks", ["All assigned tests pass"])),
        ]

        return self._write("quality.md", "\n".join(lines))

    def list_written(self) -> list[Path]:
        """Return paths of spec files currently in specs/active/."""
        return sorted(self._active.glob("*.md"))

    def _write(self, filename: str, content: str) -> Path:
        path = self._active / filename
        path.write_text(content + "\n", encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bullet_list(items: list | str) -> str:
    if isinstance(items, str):
        return f"- {items}"
    return "\n".join(f"- {textwrap.fill(str(item), width=100)}" for item in items)


def _numbered_list(items: list | str) -> str:
    if isinstance(items, str):
        return f"1. {items}"
    return "\n".join(
        f"{i + 1}. {textwrap.fill(str(item), width=100)}"
        for i, item in enumerate(items)
    )
