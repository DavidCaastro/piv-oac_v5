"""sdk/core/spec_writer.py — PHASE 0.2: interview answers → specs/active/.

Template contract (specs/_templates/INDEX.md):
  - Templates use {{variable_name}} substitution syntax.
  - SpecWriter loads the .tpl file and substitutes all variables before writing.
  - If template file missing: falls back to inline construction (graceful degradation).
  - Templates are optional enhancements — the SDK is functional without them.

Variable → source mapping for functional.md.tpl:
  {{objective}}          ← data["objective"]
  {{objective_short}}    ← data["objective"][:60]
  {{session_id}}         ← data.get("session_id", "")
  {{created_at}}         ← data.get("created_at") or current UTC timestamp
  {{scope}}              ← data["scope"] — formatted as bullet list
  {{acceptance_criteria}}← data["acceptance_criteria"] — formatted as numbered list
  {{constraints}}        ← data.get("constraints") or "(none)"
  {{out_of_scope}}       ← data.get("out_of_scope") or "(none)"
  {{task_decomposition}} ← rendered ### task:: blocks (N tasks, parseable by SpecDAGParser)
"""

from __future__ import annotations

import re
import textwrap
import time
from pathlib import Path


class SpecWriterError(Exception):
    """Raised when spec content is missing required fields."""


class SpecWriter:
    """Converts PHASE 0.1 interview answers into formal spec files.

    Output files (specs/active/):
        functional.md    — what the system must do (always written)
        architecture.md  — structural decisions (Level 2 complex only)
        quality.md       — acceptance criteria and coverage thresholds

    Template flow:
        1. Load specs/_templates/<name>.md.tpl
        2. Substitute all {{variable}} placeholders
        3. Write to specs/active/<name>.md
        4. Fallback to inline construction if template missing

    Invariant: DAG is not built and no agents are instantiated until
    the user confirms the specs written here.
    """

    REQUIRED_FUNCTIONAL_KEYS: frozenset[str] = frozenset(
        {"objective", "scope", "acceptance_criteria"}
    )

    def __init__(self, specs_dir: Path) -> None:
        self._specs     = specs_dir
        self._templates = specs_dir / "_templates"
        self._active    = specs_dir / "active"
        self._active.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_functional(self, data: dict) -> Path:
        """Write specs/active/functional.md from interview *data*.

        Required keys: objective, scope, acceptance_criteria.
        Optional keys: constraints, out_of_scope, tasks, session_id, created_at.

        'tasks': list of dicts {node_id, domain, description,
                                 depends_on (list[str]), files_in_scope (list[str]), experts (int)}
        If absent, tasks are derived from scope items (Tier 1 heuristic).
        """
        missing = self.REQUIRED_FUNCTIONAL_KEYS - set(data.keys())
        if missing:
            raise SpecWriterError(f"functional.md requires: {sorted(missing)}")

        tasks = data.get("tasks") or _derive_tasks_from_scope(
            data["scope"], data["objective"]
        )

        variables = {
            "objective":           data["objective"],
            "objective_short":     data["objective"][:60],
            "session_id":          data.get("session_id", ""),
            "created_at":          data.get("created_at") or _iso_now(),
            "scope":               _bullet_list(data["scope"]),
            "acceptance_criteria": _numbered_list(data["acceptance_criteria"]),
            "constraints":         _bullet_list(data["constraints"])
                                   if data.get("constraints") else "(none)",
            "out_of_scope":        _bullet_list(data["out_of_scope"])
                                   if data.get("out_of_scope") else "(none)",
            "task_decomposition":  _render_task_blocks(tasks),
        }

        content = self._render_template("functional.md.tpl", variables)
        return self._write("functional.md", content)

    def write_architecture(self, data: dict) -> Path:
        """Write specs/active/architecture.md (Level 2 complex only)."""
        lines = ["# Architecture Decisions", ""]
        for section, content in data.items():
            title = section.replace("_", " ").title()
            body  = _bullet_list(content) if isinstance(content, list) else str(content)
            lines += [f"## {title}", "", body, ""]
        return self._write("architecture.md", "\n".join(lines))

    def write_quality(self, data: dict) -> Path:
        """Write specs/active/quality.md."""
        lines = [
            "# Quality Criteria",
            "",
            "## Coverage Threshold",
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

    # ------------------------------------------------------------------
    # Template engine
    # ------------------------------------------------------------------

    def _render_template(self, tpl_name: str, variables: dict[str, str]) -> str:
        """Load a .tpl file and substitute all {{variable}} placeholders.

        Falls back to inline construction via _inline_functional() if the
        template file is missing (per specs/_templates/INDEX.md policy).
        """
        tpl_path = self._templates / tpl_name
        if not tpl_path.exists():
            # Graceful degradation — template is optional
            if tpl_name == "functional.md.tpl":
                return _inline_functional(variables)
            return ""  # other templates: empty fallback

        content = tpl_path.read_text(encoding="utf-8")
        # Substitute every {{key}} with its value; leave unknown placeholders as-is
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def _write(self, filename: str, content: str) -> Path:
        path = self._active / filename
        path.write_text(content if content.endswith("\n") else content + "\n",
                        encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_task_blocks(tasks: list[dict]) -> str:
    """Render a list of task dicts as ### task:: blocks (SpecDAGParser format)."""
    lines: list[str] = []
    for task in tasks:
        node_id    = task.get("node_id", "task-1")
        depends    = task.get("depends_on", [])
        files      = task.get("files_in_scope", [])
        lines += [
            f"### task::{node_id}",
            f"- **domain**: {task.get('domain', 'general')}",
            f"- **description**: {task.get('description', node_id)}",
            f"- **depends_on**: {', '.join(depends) if depends else '(none)'}",
            f"- **files_in_scope**: {', '.join(files) if files else '(tbd)'}",
            f"- **experts**: {task.get('experts', 1)}",
            "",
        ]
    return "\n".join(lines)


def _derive_tasks_from_scope(scope: list | str, objective: str) -> list[dict]:
    """Derive sequential task dicts from scope items (Tier 1 heuristic).

    Each scope item → one task. Tasks chained sequentially (each depends on previous).
    Used when no explicit tasks key is provided by the caller.
    """
    if isinstance(scope, str):
        items = [s.strip() for s in re.split(r"[,;\n]+", scope) if s.strip()]
    else:
        items = [str(s).strip() for s in scope if str(s).strip()]

    if not items:
        items = [objective[:120]]

    tasks: list[dict] = []
    prev_id: str | None = None
    for i, item in enumerate(items):
        slug    = re.sub(r"[^a-z0-9]+", "-", item.lower())[:40].strip("-")
        node_id = slug or f"task-{i + 1}"
        tasks.append({
            "node_id":        node_id,
            "domain":         "general",
            "description":    item,
            "depends_on":     [prev_id] if prev_id else [],
            "files_in_scope": [],
            "experts":        1,
        })
        prev_id = node_id

    return tasks


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


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _inline_functional(v: dict[str, str]) -> str:
    """Inline fallback when functional.md.tpl is missing."""
    lines = [
        f"# Functional Spec — {v['objective_short']}",
        "",
        f"## Objective",
        "",
        v["objective"],
        "",
        "## Scope",
        "",
        v["scope"],
        "",
        "## Acceptance Criteria",
        "",
        v["acceptance_criteria"],
    ]
    if v["constraints"] != "(none)":
        lines += ["", "## Constraints", "", v["constraints"]]
    if v["out_of_scope"] != "(none)":
        lines += ["", "## Out of Scope", "", v["out_of_scope"]]
    lines += [
        "",
        "---",
        "",
        "## Task Decomposition",
        "",
        "<!-- Parsed by sdk/core/dag.SpecDAGParser -->",
        "",
        v["task_decomposition"],
    ]
    return "\n".join(lines)
