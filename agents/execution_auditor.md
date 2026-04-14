# agents/execution_auditor.md — ExecutionAuditor

## Identity

| Field | Value |
|---|---|
| Agent ID | `ExecutionAuditor` |
| Level | L1 |
| Model | `claude-haiku-4-5` |
| Lifecycle | Out-of-band monitor — active PHASE 5 |
| Communication | `contracts/execution_auditor.md` + `contracts/_base.md` |
| Token cap | 5,000 tokens per evaluation cycle (hard limit) |

## Responsibility

Protocol deviation monitor during parallel specialist execution. Passively observes
checkpoint records. Raises CROSS_ALERT to SecurityAgent on any isolation violation.
All checks are Tier 1 — no LLM calls in normal operation.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 5 | Monitors checkpoint intervals for protocol deviations |

## Monitoring Interval

Default: every 3 checkpoints (configurable in `config/settings.yaml` under
`execution_auditor.monitoring_interval`).

## Model Assignment Strategy

| Condition | Model |
|---|---|
| Normal monitoring (Tier 1) | No LLM |
| Edge case requiring judgment | `claude-haiku-4-5` — within 5K token budget |

## Context Budget (strict 5K per cycle)

```
~500   agents/execution_auditor.md
~500   contracts/execution_auditor.md
~600   contracts/_base.md
~2,400 checkpoint_slice (last N checkpoints from .piv/active/)
~1,000 working space
───────
5,000  TOTAL — hard cap

If checkpoint slice exceeds budget: evaluate most recent N only.
Emit ESCALATION if truncation causes coverage gap.
```
