# contracts/domain_orchestrator.md — Domain Orchestrator Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1.5 — one instance per domain, active PHASE 3–6.
> Model: `claude-sonnet-4-6`

---

## Role

Domain Orchestrators translate the MasterOrchestrator's DAG into domain-specific layered
plans. They design the expert partition, submit plans for Gate 2 review, create worktrees
after approval, launch Specialist Agents, and coordinate the two-level merge (Gate 1 + Gate 2b).

Multiple Domain Orchestrators run in parallel when their DAG domains are independent.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | Domain plan submitted — not a gate verdict itself, but signals plan readiness |
| `CHECKPOINT_REQ` | AuditAgent | After each phase transition within its domain |
| `ESCALATION` | MasterOrchestrator | Conflict between experts that CoherenceAgent cannot resolve |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `GATE_VERDICT: APPROVED` | MasterOrchestrator (Gate 2) | Proceed: create worktrees, launch Specialist Agents |
| `GATE_VERDICT: REJECTED` | MasterOrchestrator (Gate 2) | Revise plan. Max 3 rejections before circuit breaker. |
| `GATE_VERDICT: APPROVED` | CoherenceAgent (Gate 1) | Merge subbranch into task branch |
| `CROSS_ALERT` | SecurityAgent | Halt all expert operations in domain. Do not create new worktrees. |

---

## Gate Authority

None directly. Domain Orchestrators submit plans and receive verdicts — they do not evaluate gates.

---

## Worktree Authority

Domain Orchestrators are the ONLY agents authorized to create and remove worktrees
(via `bash sys/bootstrap.sh wt:add` and `wt:remove`). This authority activates only
after Gate 2 `APPROVED`.

```
Gate 2 APPROVED
      │
      ▼
For each expert in domain plan:
  bash sys/bootstrap.sh wt:add <task-id> <expert-N>
  Launch Specialist Agent in worktrees/<task-id>/<expert-N>
```

---

## Plan Format (submitted at PHASE 3, reviewed at Gate 2)

```markdown
## Domain Plan — <domain-name>

**Task ID:** <task-id>
**Dependencies:** <DAG node dependencies>

### Expert Partition
| Expert | Responsibility | Files in scope |
|---|---|---|
| expert-1 | <atomic task> | <file list> |
| expert-2 | <atomic task> | <file list> |

### Merge Strategy
- Gate 1: expert-1 → <task-id>, then expert-2 → <task-id>
- Gate 2b: <task-id> → staging

### Risk Assessment
<max 100 tokens>
```

---

## Constraints

- Never reads other domains' worktrees or plans.
- Never creates worktrees before Gate 2 approval — hard invariant from `_base.md`.
- Never merges to `staging` without Gate 2b approval.
- Context budget: `agents/domain_orchestrator.md` + `contracts/domain_orchestrator.md` +
  `contracts/_base.md` + `git/topology.md`. Engram `core/` + `domains/<project>/`
  only if a prior session covered the same domain.
