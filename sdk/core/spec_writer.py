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
        Optional: constraints, out_of_scope, tasks.

        The 'tasks' key, if provided, is a list of dicts with keys:
            node_id, domain, description, depends_on (list[str]), files_in_scope (list[str]), experts (int)
        If 'tasks' is absent, tasks are derived from the scope items.

        The generated functional.md includes a '## Task Decomposition' section
        with '### task::<node_id>' blocks parseable by sdk/core/dag.SpecDAGParser.
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

        # Task Decomposition — parseable by SpecDAGParser
        tasks = data.get("tasks") or _derive_tasks_from_scope(
            data["scope"], data["objective"]
        )
        lines += ["", "---", "", "## Task Decomposition", ""]
        lines += [
            "<!-- Task blocks below are parsed by sdk/core/dag.SpecDAGParser. -->",
            "<!-- Format: ### task::<node_id> followed by key: value lines.  -->",
            "",
        ]
        for task in tasks:
            lines += _task_block(task)

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


def _task_block(task: dict) -> list[str]:
    """Render a single task dict as a ### task:: block (SpecDAGParser format)."""
    node_id = task.get("node_id", "task-1")
    depends = task.get("depends_on", [])
    depends_str = ", ".join(depends) if depends else "(none)"
    files = task.get("files_in_scope", [])
    files_str = ", ".join(files) if files else "(tbd)"
    experts = task.get("experts", 1)

    return [
        f"### task::{node_id}",
        f"- **domain**: {task.get('domain', 'general')}",
        f"- **description**: {task.get('description', node_id)}",
        f"- **depends_on**: {depends_str}",
        f"- **files_in_scope**: {files_str}",
        f"- **experts**: {experts}",
        "",
    ]


def _derive_tasks_from_scope(scope: list | str, objective: str) -> list[dict]:
    """Derive sequential task dicts from scope items (Tier 1 heuristic).

    Each scope item becomes one task. Tasks are chained sequentially
    (each depends on the previous). This is a best-effort decomposition
    when no explicit tasks are provided by the caller.
    """
    import re

    if isinstance(scope, str):
        # Split on commas, semicolons, or newlines
        items = [s.strip() for s in re.split(r"[,;\n]+", scope) if s.strip()]
    else:
        items = [str(s).strip() for s in scope if str(s).strip()]

    if not items:
        items = [objective[:120]]

    tasks = []
    prev_id: str | None = None
    for i, item in enumerate(items):
        # node_id: slugify the item (keep alphanumeric + hyphen, max 40 chars)
        slug = re.sub(r"[^a-z0-9]+", "-", item.lower())[:40].strip("-")
        node_id = slug or f"task-{i + 1}"

        task: dict = {
            "node_id": node_id,
            "domain": "general",
            "description": item,
            "depends_on": [prev_id] if prev_id else [],
            "files_in_scope": [],
            "experts": 1,
        }
        tasks.append(task)
        prev_id = node_id

    return tasks
