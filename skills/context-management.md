# skills/context-management.md — Context Management

## When to Load

When managing context budgets, lazy loading, or context saturation recovery.

## Core Rule

Load the minimum context required to complete the current task.
Never pre-load. Declare what you need and why before loading.

## Load Order (by priority)

1. Own agent definition file (`agents/<role>.md`)
2. Own contract (`contracts/<role>.md`)
3. Base contract (`contracts/_base.md`)
4. Task spec (`specs/active/<task>.md`) — own task only
5. Skills — declared, SHA-256 verified, on-demand only
6. Engram atoms — conditional, role-scoped, justified

## Context Budget Tiers

| Agent | Hard Cap | Action at 80% |
|---|---|---|
| L0 MasterOrchestrator | Model window | ESCALATION: CONTEXT_SATURATION |
| L1 Control agents | Model window | ESCALATION: CONTEXT_SATURATION |
| L2 SpecialistAgent | Model window | ESCALATION at 80% |
| ExecutionAuditor | 5,000 tokens | Hard stop — evaluate most recent N only |

## Saturation Recovery

```
ESCALATION: CONTEXT_SATURATION
→ MasterOrchestrator receives
→ Decides: pause session (save state to .piv/) or spawn sub-agent
→ SecurityAgent: fragment into sub-agents (×6 max)
→ State preserved in .piv/active/<session_id>.json
```

## What NOT to Load

- Files outside own role's authorized list
- Engram atoms not relevant to current task
- Other agents' task specs
- Historical sessions (unless AuditAgent retrieving for pattern analysis)
- Product source code (agents read specs, not source)
