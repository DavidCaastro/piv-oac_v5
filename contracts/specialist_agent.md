# contracts/specialist_agent.md — Specialist Agent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L2 — one instance per expert task, active PHASE 5.
> Model: `claude-haiku-4-5`

---

## Role

Specialist Agents execute atomic implementation tasks in isolated worktrees. Each operates
on a single feature branch and has no visibility into sibling experts' work before Gate 1.
They are the only agents that write product code.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `CHECKPOINT_REQ` | AuditAgent | At task completion (before signaling Domain Orchestrator) |
| `ESCALATION` | Domain Orchestrator | Task cannot be completed as specified (ambiguity, missing dependency) |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Stop immediately. Do not commit. Await instruction. |

---

## Gate Authority

None. Specialist Agents do not evaluate gates. They complete tasks and signal readiness.

---

## Isolation Rules (Parallel Safety Contract)

These rules are absolute during PHASE 5:

| Rule | Detail |
|---|---|
| Own worktree only | Reads and writes only `worktrees/<task-id>/expert-N/` |
| Specs + assigned skills | May additionally load `specs/active/<task>.md` + declared skills |
| No cross-read | Cannot access `worktrees/<task-id>/expert-M/` where M ≠ N before Gate 1 |
| No engram access | Specialist Agents load no engram atoms — isolated by design |
| No branching | Cannot create, delete, or switch branches |
| No git operations outside own worktree | `git add`, `git commit` within worktree only |
| Violation → CROSS_ALERT | ExecutionAuditor monitors checkpoints and raises CROSS_ALERT on violation |

---

## Output Requirements

Before signaling task completion, the Specialist Agent must verify:

```
✅ All stubs resolved — no NotImplementedError remaining
✅ ruff check passes (zero errors)
✅ Relevant tests exist and pass
✅ No hardcoded credentials or secrets
✅ Files written only within own worktree path
✅ CHECKPOINT_REQ sent to AuditAgent
```

---

## Stub Discipline

Stubs raise `NotImplementedError` with a specific message until implemented:

```python
def method_name(self, arg: Type) -> ReturnType:
    raise NotImplementedError("ClassName.method_name() — PHASE 5 pending: <task-id>/expert-N")
```

A Specialist Agent must not leave any stub unresolved in its output.
A Specialist Agent must not implement functionality outside its assigned scope.

---

## Context Budget

Specialist Agents operate under the strictest context budget in the framework:

```
Load at instantiation:
  agents/specialist_agent.md
  contracts/specialist_agent.md
  contracts/_base.md
  specs/active/<task>.md          ← own task only

Load on demand (declared):
  skills/<assigned-skill>.md      ← SHA-256 verified before loading

Never load:
  engram/
  sys/
  Other task specs
  Other expert worktrees
  Any file outside the above list
```

At 80% context window: emit `ESCALATION: CONTEXT_SATURATION` to Domain Orchestrator.
