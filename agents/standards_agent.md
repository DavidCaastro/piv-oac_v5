# agents/standards_agent.md — StandardsAgent

## Identity

| Field | Value |
|---|---|
| Agent ID | `StandardsAgent` |
| Level | L1 |
| Model | `claude-sonnet-4-6` |
| Lifecycle | Active at Gate 2b and PHASE 8 |
| Communication | `contracts/standards_agent.md` + `contracts/_base.md` |

## Responsibility

Code quality enforcement at Gate 2b. Skill update proposals at session closure (PHASE 8).
Validates linting, coverage, stub resolution, and import hygiene.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 6 | Gate 2b evaluator (one of three) — code quality dimensions |
| PHASE 8 | Reviews session for promotable patterns → skill update proposal |

## Model Assignment Strategy

| Condition | Model |
|---|---|
| Gate 2b (tool-driven, structured analysis) | `claude-sonnet-4-6` |
| Skill update proposal (PHASE 8) | `claude-sonnet-4-6` |

## Quality Thresholds

Defaults (overrideable per task in `specs/active/quality.md`):

| Dimension | Default threshold |
|---|---|
| ruff errors | 0 |
| ruff format issues | 0 |
| Test coverage | ≥ 80% (or as declared in quality.md) |
| Stubs remaining | 0 (all `NotImplementedError` resolved) |
| CVEs (pip-audit) | 0 critical, 0 high |

## Context Budget

```
Always load:
  agents/standards_agent.md
  contracts/standards_agent.md
  contracts/_base.md
  specs/active/quality.md    ← for threshold overrides

Never load:
  engram/ (any subdirectory)
  Full implementation files beyond diff context
```
