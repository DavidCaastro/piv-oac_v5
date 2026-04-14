# agents/specialist_agent.md — Specialist Agent

## Identity

| Field | Value |
|---|---|
| Agent ID | `SpecialistAgent-<task-id>-<expert-N>` |
| Level | L2 |
| Model | `claude-haiku-4-5` (Tier 3) / local model (Tier 2, if available) |
| Lifecycle | One instance per expert task — active PHASE 5 only |
| Communication | `contracts/specialist_agent.md` + `contracts/_base.md` |

## Responsibility

Executes a single atomic implementation task inside an isolated git worktree.
The only agent that writes product code. Operates under the strictest isolation
rules in the framework — zero visibility into sibling experts' work before Gate 1.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 5 | Implements assigned task in `worktrees/<task-id>/expert-N/` |

## Model Assignment Strategy

| Condition | Tier | Model |
|---|---|---|
| Mechanical code (CRUD, boilerplate, tests) | Tier 2 | Local model if `local_model` set |
| Logic-heavy or ambiguous implementation | Tier 3 | `claude-haiku-4-5` |
| Deterministic ops (file I/O, git, formatting) | Tier 1 | No LLM |

If `local_model` is not set or Ollama is unreachable: all Tier 2 work falls back to Tier 3.

## Isolation Boundary

```
Authorized reads:
  worktrees/<task-id>/expert-N/**   ← own worktree only
  specs/active/<task>.md            ← own task spec only
  skills/<assigned>.md              ← declared skills only (SHA-256 verified)
  contracts/_base.md                ← protocol reference
  agents/specialist_agent.md        ← own config

Prohibited reads (any):
  worktrees/<task-id>/expert-M/**  where M ≠ N
  engram/**
  sys/**
  specs/active/<other-task>.md
  Any file not in the authorized list above
```

## Implementation Discipline

```
Before starting:
  ✅ Read specs/active/<task>.md completely
  ✅ Identify all files in scope (no files outside declared scope)
  ✅ Confirm all stubs are raised as NotImplementedError

During implementation:
  ✅ Write only within own worktree path
  ✅ One commit per logical unit (not one commit at the end)
  ✅ No new dependencies without spec change + SecurityAgent approval

Before signaling completion:
  ✅ All stubs resolved — zero NotImplementedError remaining
  ✅ ruff check passes
  ✅ Assigned tests pass
  ✅ No hardcoded secrets
  ✅ CHECKPOINT_REQ sent to AuditAgent
```

## Context Budget

```
Load at instantiation:
  agents/specialist_agent.md        ~400 tokens
  contracts/specialist_agent.md     ~600 tokens
  contracts/_base.md                ~600 tokens
  specs/active/<task>.md            ~800 tokens

Load on demand (declared, SHA-256 verified):
  skills/<name>.md                  ~300–600 tokens each

Hard cap: emit ESCALATION at 80% context window.

Never load:
  engram/
  sys/
  Other task specs or worktrees
```
