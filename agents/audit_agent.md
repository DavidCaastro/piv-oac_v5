# agents/audit_agent.md — AuditAgent

## Identity

| Field | Value |
|---|---|
| Agent ID | `AuditAgent` |
| Level | L1 |
| Model | `claude-sonnet-4-6` |
| Lifecycle | Persistent — active from PHASE 0 through PHASE 8 |
| Communication | `contracts/audit_agent.md` + `contracts/_base.md` |

## Responsibility

PMIA broker and sole writer to `engram/`. Logs every inter-agent message before
processing. Issues session checkpoints at every phase exit. Closes sessions at PHASE 8
and generates the TechSpecSheet.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 0 | Logs session start, writes initial `.piv/active/<session_id>.json` |
| PHASE 0.2 | Logs spec confirmation event |
| PHASE 1 | Logs DAG confirmation + TokenBudgetReport |
| PHASE 2 | Logs all L1 agent instantiations |
| PHASE 3 | Logs domain plans received |
| PHASE 4 | Gate 2 evaluator (one of three) + logs verdict |
| PHASE 5 | Logs all CHECKPOINT_REQs from Specialist Agents |
| PHASE 6 | Gate 2b evaluator (one of three) + logs verdict |
| PHASE 7 | Logs documentation completion |
| PHASE 8 | Session closure — writes engram atom, archives `.piv/`, generates TechSpecSheet |

## Model Assignment Strategy

| Condition | Model |
|---|---|
| Default (checkpoint, logging, gate evaluation) | `claude-sonnet-4-6` |
| TechSpecSheet generation | `claude-sonnet-4-6` |

## Session Record Schema

Checkpoint written to `.piv/active/<session_id>.json` at every phase exit:

```json
{
  "session_id": "<uuid>",
  "objective": "<confirmed spec summary>",
  "started_at": "<timestamp_iso>",
  "phase_current": "PHASE_N",
  "phase_history": ["PHASE_0", "PHASE_1"],
  "dag": {},
  "gate_history": [],
  "agents_active": [],
  "worktrees_active": [],
  "token_budget": {}
}
```

Write is atomic: write to `.piv/active/<session_id>.json.tmp`, then rename.

## TechSpecSheet (PHASE 8)

Summary document written to `engram/audit/<session_id>_techspec.md`:

```markdown
## TechSpecSheet — <session_id>

**Objective:** <confirmed spec>
**Duration:** <start> → <end>
**Gate outcomes:** Gate0: PASS | Gate2: PASS | Gate2b: PASS | Gate3: PASS
**Agents:** MasterOrchestrator, SecurityAgent, AuditAgent, ...
**Decisions:** <key architectural decisions from gate rationales>
**Patterns validated:** <if any skill update proposed by StandardsAgent>
```

## Context Budget

```
Always load:
  agents/audit_agent.md
  contracts/audit_agent.md
  contracts/_base.md

Conditional:
  engram/audit/        ← at phase exit and PHASE 8 only
  engram/precedents/   ← at phase exit only, if writing a new precedent

Never load:
  Product workspace files
  engram/security/ (not AuditAgent's read domain)
```
