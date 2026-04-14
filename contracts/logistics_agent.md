# contracts/logistics_agent.md — LogisticsAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — active at PHASE 1 (DAG construction).
> Model: `claude-haiku-4-5`

---

## Role

LogisticsAgent performs resource analysis before the DAG is confirmed. It issues a
TokenBudgetReport that informs the MasterOrchestrator of the estimated token cost and
parallelism potential of the proposed execution plan. This runs entirely at Tier 1 —
no LLM calls are made by LogisticsAgent itself.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `CHECKPOINT_REQ` | AuditAgent | After issuing TokenBudgetReport |
| `ESCALATION` | MasterOrchestrator | DAG estimated cost exceeds session budget threshold |

---

## Messages Received

None — LogisticsAgent is invoked directly by MasterOrchestrator at PHASE 1.

---

## Gate Authority

None. LogisticsAgent is advisory. Its report informs the DAG but does not block it.

---

## TokenBudgetReport Format

Computed deterministically (Tier 1) from the proposed DAG structure:

```json
{
  "session_id": "<uuid>",
  "phase": "PHASE_1",
  "agent": "LogisticsAgent",
  "dag_summary": {
    "total_tasks": 6,
    "parallel_groups": 2,
    "max_parallelism": 3,
    "critical_path_length": 4
  },
  "budget_estimate": {
    "tier1_ops": 42,
    "tier2_tokens": 0,
    "tier3_tokens_estimated": 18400,
    "tier3_cost_usd_estimated": 0.09
  },
  "risk_flags": [],
  "recommendation": "PROCEED | REVIEW_SCOPE | SPLIT_SESSION",
  "timestamp_ms": 1744790781342
}
```

`recommendation` thresholds (configurable in `config/settings.yaml`):
- `PROCEED`: estimated tokens ≤ 80% of session budget
- `REVIEW_SCOPE`: 80–100% of session budget — MasterOrchestrator should consider splitting
- `SPLIT_SESSION`: > 100% — DAG must be split before proceeding

---

## Estimation Algorithm (Tier 1 — deterministic)

```
per_task_estimate(task):
  base = complexity_score(task) × tokens_per_complexity_point
  files = len(task.files_in_scope) × tokens_per_file_read
  return base + files

total = sum(per_task_estimate(t) for t in dag.tasks)
       + L0_overhead + L1_control_overhead
       + gate_evaluations × tokens_per_gate
```

All constants defined in `config/settings.yaml`. No LLM call involved.

---

## Constraints

- All computation is Tier 1 — no LLM calls, no external requests.
- Report is advisory — MasterOrchestrator decides whether to proceed.
- Never reads product workspace files or `engram/`.
- Context budget: `agents/logistics_agent.md` + `contracts/logistics_agent.md` +
  `contracts/_base.md`. No additional files.
