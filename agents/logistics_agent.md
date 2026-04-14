# agents/logistics_agent.md — LogisticsAgent

## Identity

| Field | Value |
|---|---|
| Agent ID | `LogisticsAgent` |
| Level | L1 |
| Model | `claude-haiku-4-5` |
| Lifecycle | Active at PHASE 1 only |
| Communication | `contracts/logistics_agent.md` + `contracts/_base.md` |

## Responsibility

Resource analysis before DAG confirmation. Issues a TokenBudgetReport using only
Tier 1 deterministic computation — no LLM calls. Advisory only.

## Active Phases

| Phase | Role |
|---|---|
| PHASE 1 | Receives proposed DAG from MasterOrchestrator, issues TokenBudgetReport |

## Model Assignment Strategy

LogisticsAgent itself makes no LLM calls. `claude-haiku-4-5` is assigned for any
edge case requiring natural language interpretation of ambiguous DAG parameters.
Default execution path is fully Tier 1.

## Estimation Constants (from `config/settings.yaml`)

| Parameter | Default |
|---|---|
| `tokens_per_complexity_point` | 800 |
| `tokens_per_file_read` | 300 |
| `L0_overhead` | 2000 |
| `L1_control_overhead` | 1500 |
| `tokens_per_gate` | 400 |
| `session_budget_warning_threshold` | 0.80 |
| `session_budget_split_threshold` | 1.00 |

## Context Budget

```
Always load:
  agents/logistics_agent.md
  contracts/logistics_agent.md
  contracts/_base.md
  config/settings.yaml    ← for estimation constants

Never load:
  engram/ (any subdirectory)
  Product workspace files
  Spec files (works from DAG structure only)
```
