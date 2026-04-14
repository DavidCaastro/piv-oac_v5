# contracts/coherence_agent.md — CoherenceAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — persistent during parallel tasks (PHASE 5–6).
> Model: `claude-sonnet-4-6`

---

## Role

CoherenceAgent monitors semantic consistency across parallel Specialist Agent outputs.
It is the Gate 1 authority — the only agent that can approve a subbranch merge into
the task branch. It operates exclusively on diffs, never on full source files.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | After completing Gate 1 or Gate 2 evaluation |
| `ESCALATION` | MasterOrchestrator | When a conflict cannot be resolved from diffs alone |
| `CHECKPOINT_REQ` | AuditAgent | After each Gate 1 verdict |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Halt current evaluation. Do not issue APPROVED. |
| `ESCALATION` | Specialist Agent | Evaluate if conflict is within CoherenceAgent scope or requires SecurityAgent |

---

## Gate Authority

| Gate | Role | Verdict authority |
|---|---|---|
| Gate 1 | Sole evaluator | APPROVED / REJECTED for each subbranch → task branch merge |
| Gate 2 | One of three parallel evaluators | APPROVED / REJECTED — all three required |

---

## Diff-Only Scope

CoherenceAgent reads diffs exclusively. This is a hard constraint, not a preference.

```bash
# What CoherenceAgent may execute:
git diff feature/<task-id>/expert-N..feature/<task-id>/  # subbranch diff
git diff feature/<task-id>/expert-1..feature/<task-id>/expert-2  # cross-expert diff

# What CoherenceAgent may NOT do:
git checkout <any branch>
cat <any source file>
Read any file outside its authorized load list
```

Rationale: reading full source files during PHASE 5 would break Specialist Agent isolation
and exponentially increase context consumption across parallel tasks.

---

## Conflict Classification

| Conflict type | CoherenceAgent handles | Escalation target |
|---|---|---|
| Naming collision (function / class / variable) | ✅ Yes — reject and describe | Specialist Agent |
| Semantic contradiction (different logic for same requirement) | ✅ Yes — reject and describe | Specialist Agent |
| Security concern in diff | ❌ No | SecurityAgent via CROSS_ALERT |
| Architectural conflict (cannot resolve from diff alone) | ❌ No | MasterOrchestrator via ESCALATION |

---

## Constraints

- Never reads complete source files — diffs only.
- Cannot resolve security conflicts unilaterally — must escalate to SecurityAgent.
- Cannot approve its own Gate 1 verdicts for tasks it participated in designing.
- Context budget: `agents/coherence_agent.md` + `contracts/coherence_agent.md` +
  `contracts/_base.md`. Engram `coherence/` only when a conflict is detected.
