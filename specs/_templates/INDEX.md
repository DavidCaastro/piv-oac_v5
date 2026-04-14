# specs/_templates/INDEX.md — Spec Templates Index

Templates used by `sdk/core/spec_writer.py` to scaffold `specs/active/` files.

---

## Available Templates

| Template | Used by | Phase |
|---|---|---|
| `functional.md.tpl` | SpecWriter.write_functional() | PHASE 0.2 |
| `architecture.md.tpl` | SpecWriter.write_architecture() | PHASE 0.2 (Level 2 complex) |
| `quality.md.tpl` | SpecWriter.write_quality() | PHASE 0.2 |
| `research.md.tpl` | ResearchOrchestrator (PHASE 8) | RESEARCH mode |
| `ci/pre-commit-config.yaml` | piv-oac init (Mode 2) | init bootstrap |

---

## Template Variables

All templates use `{{variable_name}}` syntax. SpecWriter substitutes values
from the interview transcript before writing.

### functional.md.tpl variables

| Variable | Source |
|---|---|
| `{{objective}}` | Interview answer: "What is the goal?" |
| `{{scope}}` | Interview answer: "What must be delivered?" |
| `{{acceptance_criteria}}` | Interview answer: "How do we know it's done?" |
| `{{constraints}}` | Interview answer: "What are the limits?" (optional) |
| `{{out_of_scope}}` | Interview answer: "What is explicitly excluded?" (optional) |

### quality.md.tpl variables

| Variable | Source |
|---|---|
| `{{coverage_threshold}}` | Interview answer or default (80) |
| `{{acceptance_checks}}` | Derived from functional.md acceptance_criteria |

---

## Template Location

Templates are stored in `specs/_templates/` and bundled via `pyproject.toml`
`package_data` (so they are available after `pip install piv-oac`).

When SpecWriter cannot find a template file, it falls back to inline defaults.
Templates are optional enhancements — the SDK is functional without them.
