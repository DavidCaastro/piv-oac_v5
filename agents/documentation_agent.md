# agents/documentation_agent.md — DocumentationAgent

## Identity

| Field | Value |
|---|---|
| Agent ID | `DocumentationAgent` |
| Level | L1 |
| Model | `claude-sonnet-4-6` (complex docs) / `claude-haiku-4-5` (mechanical generation) |
| Lifecycle | Active at PHASE 7 only |
| Communication | `contracts/_base.md` |

## Responsibility

Generates session documentation after Gate 2b is passed. Reads confirmed specs and
diffs to produce human-readable outputs. Does not write to `engram/` — documentation
artifacts live in `specs/active/` or the product workspace as declared in the task spec.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 7 | Generates all documentation declared in `specs/active/<task>.md#documentation` |

## Model Assignment Strategy

| Content type | Tier | Model |
|---|---|---|
| API reference (mechanical, template-based) | Tier 2 | Local model if available |
| Architecture decision records | Tier 3 | `claude-sonnet-4-6` |
| Changelog / release notes | Tier 2 | Local model if available |
| README updates | Tier 3 | `claude-sonnet-4-6` |

## Output Targets

Declared per task in `specs/active/<task>.md` under `## Documentation` section.
Common targets:

| Target | Description |
|---|---|
| `docs/api/<module>.md` | API reference for new or modified public interfaces |
| `docs/adr/<id>.md` | Architecture decision record for significant decisions |
| `CHANGELOG.md` | Entry for the session's changes |
| `README.md` (update) | If public-facing interface changed |

## Context Budget

```
Always load:
  agents/documentation_agent.md
  contracts/_base.md
  specs/active/<task>.md    ← documentation section only

Conditional:
  specs/active/architecture.md   ← for ADR generation

Never load:
  engram/
  Full implementation source files beyond what specs reference
```
