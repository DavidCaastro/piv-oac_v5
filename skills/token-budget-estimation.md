# skills/token-budget-estimation.md — Token Budget Estimation

## When to Load

When LogisticsAgent generates a TokenBudgetReport before DAG confirmation.

## Estimation Constants (config/settings.yaml defaults)

| Parameter | Default | Used for |
|---|---|---|
| `tokens_per_complexity_point` | 800 | Per DAG node complexity |
| `tokens_per_file_read` | 300 | Per file loaded by any agent |
| `L0_overhead` | 2000 | MasterOrchestrator base cost |
| `L1_control_overhead` | 1500 | Per control agent (× agent count) |
| `tokens_per_gate` | 400 | Per gate evaluation |
| `session_budget_warning_threshold` | 0.80 | Warn at 80% of model limit |
| `session_budget_split_threshold` | 1.00 | Recommend split at 100% |

## Estimation Algorithm

```
total_estimate =
    L0_overhead
  + (number_of_L1_agents × L1_control_overhead)
  + (number_of_nodes × avg_complexity × tokens_per_complexity_point)
  + (estimated_file_reads × tokens_per_file_read)
  + (number_of_gates × tokens_per_gate)
```

## TokenBudgetReport JSON Format

```json
{
  "session_id": "<uuid>",
  "dag_node_count": 4,
  "estimated_tokens": 28000,
  "model_context_limit": 200000,
  "utilization_ratio": 0.14,
  "recommendation": "PROCEED",
  "warnings": [],
  "split_suggestions": []
}
```

## Recommendations

| Utilization | Recommendation |
|---|---|
| < 0.80 | `PROCEED` — session fits comfortably |
| 0.80 – 1.00 | `REVIEW_SCOPE` — consider reducing node count |
| > 1.00 | `SPLIT_SESSION` — DAG must be split across sessions |

## LogisticsAgent Model

All computation is Tier 1 (arithmetic only). No LLM call.
`claude-haiku-4-5` is available only for edge cases (ambiguous DAG parameters).
