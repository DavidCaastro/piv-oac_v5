# skills/token-budget-estimation.md — Token Budget Estimation

## When to Load

When LogisticsAgent generates a TokenBudgetReport before DAG confirmation, or when
any agent needs to evaluate whether a task fits within session token limits.

---

## Estimation Constants (config/settings.yaml defaults)

| Parameter | Default | Used for |
|---|---|---|
| `tokens_per_complexity_point` | 800 | Per DAG node complexity unit |
| `tokens_per_file_read` | 300 | Per file loaded by any agent |
| `L0_overhead` | 2000 | OrchestratorAgent base cost |
| `L1_control_overhead` | 1500 | Per L1 control agent (× agent count) |
| `L1_5_tool_overhead` | 1200 | Per L1.5 tool-augmented agent (× agent count) |
| `L2_expert_overhead` | 3000 | Per L2 expert agent invocation |
| `tokens_per_gate` | 400 | Per gate evaluation |
| `session_budget_warning_threshold` | 0.75 | Warn at 75% of model limit |
| `session_budget_critical_threshold` | 0.90 | Critical alert at 90% |
| `session_budget_split_threshold` | 1.00 | Force split at 100% |
| `checkpoint_compression_ratio` | 0.40 | Expected context reduction after compression |

---

## Per-Agent Token Caps

Hard limits enforced by TelemetryLogger. Exceeding `max_per_call` causes the
current invocation to be truncated and logged. Exceeding `session_aggregate`
triggers `ESCALATION(AGENT_QUOTA_EXCEEDED)`.

| Agent | Max per invocation | Session aggregate cap |
|---|---|---|
| OrchestratorAgent (L0) | 8,000 | 40,000 |
| SecurityAgent (L1) | 4,000 | 30,000 |
| ExpertAgent (L2) | 12,000 | 60,000 |
| CoherenceAgent (L1) | 6,000 | 20,000 |
| AuditAgent (L1.5) | 3,000 | 15,000 |
| StandardsAgent | 0 (Tier 1 — no LLM tokens) | 0 |
| DocumentationAgent | 8,000 | 35,000 |
| LogisticsAgent | 2,000 (edge cases only) | 10,000 |

---

## Task-Level Token Caps

Used by LogisticsAgent to set the session budget ceiling before DAG execution begins.
These caps apply to the entire session, across all agents combined.

| Task Size | Definition | Session Token Cap |
|---|---|---|
| microtask | < 50 lines changed, single file | 8,000 |
| simple | 50–200 lines changed, ≤2 files | 20,000 |
| standard | 200–500 lines changed, ≤5 files | 50,000 |
| complex | 500+ lines OR DAG with 3+ nodes | 120,000 |
| framework meta | PIV/OAC self-modification (sdk/, agents/, contracts/) | 200,000 |

Task size is determined by LogisticsAgent from the task spec and estimated diff
scope. When ambiguous, round up to the next tier.

---

## Estimation Algorithm

All computation is Tier 1 (pure arithmetic). No LLM call required.

```
total_estimate =
    L0_overhead
  + (count_L1_agents  × L1_control_overhead)
  + (count_L1_5_agents × L1_5_tool_overhead)
  + (count_L2_agents  × L2_expert_overhead)
  + (dag_node_count   × avg_complexity × tokens_per_complexity_point)
  + (estimated_file_reads × tokens_per_file_read)
  + (gate_count       × tokens_per_gate)
```

### Per-Node DAG Estimation

For each node `n` in the DAG:

```
node_estimate(n) =
    agent_overhead(n.agent_level)
  + (n.complexity_score × tokens_per_complexity_point)
  + (n.estimated_file_reads × tokens_per_file_read)
  + (n.gate_count × tokens_per_gate)
```

### Aggregate DAG Estimate

```
dag_total = sum(node_estimate(n) for n in dag.nodes)
           + L0_overhead                  # orchestrator always present
           + (dag.parallel_branches × 500) # coordination overhead per branch
```

`utilization_ratio = dag_total / model_context_limit`

If `utilization_ratio > 1.0`: recommend `SPLIT_SESSION` before execution begins.

---

## Real-Time Alerting Thresholds

TelemetryLogger monitors cumulative token consumption throughout the session and
triggers the following actions:

| Threshold | Action |
|---|---|
| 50% | `LOG INFO` — nominal progress marker |
| 60% | `CHECKPOINT_REQ` + begin context compression (6-step protocol below) |
| 75% | `LOG WARN` + include metric in telemetry report |
| 80% | `VETO_SATURACIÓN` candidate — evaluate task split feasibility |
| 90% | `CRITICAL` alert — force checkpoint + notify OrchestratorAgent immediately |
| 100% | `ESCALATION(CONTEXT_SATURATION)` — halt current phase, do not proceed |

### 6-Step Context Compression Protocol (triggered at 60%)

1. Summarize completed phases into a single compressed summary block
2. Drop raw file contents already processed (retain only diffs and decisions)
3. Retain only the last 2 exchanges per agent in the working context
4. Keep all gate verdicts and ESCALATION events verbatim (never compress these)
5. Recalculate `utilization_ratio` after compression
6. If post-compression ratio is still > 0.75, escalate to `VETO_SATURACIÓN`

---

## Model Degradation Cost Table

When budget is constrained, downgrade to a cheaper model to extend the session.
The `When to downgrade` column gives the signal, not a mandate.

| Model | Input cost / 1M tokens | Output cost / 1M tokens | When to downgrade |
|---|---|---|---|
| claude-opus-4-6 | high | high | Always preferred for complex reasoning; downgrade only on budget pressure |
| claude-sonnet-4-6 | mid | mid | When budget remaining < 50% and task is still L1 complexity |
| claude-haiku-4-5-20251001 | low | low | When budget remaining < 25%, or task is simple/mechanical |
| gpt-4o | mid | mid | OpenAI preference or cross-provider fallback |
| gpt-4o-mini | low | low | High-volume simple tasks; structured output with JSON mode |
| Ollama (local) | zero | zero | Always preferred for privacy-scoped tasks; no cost constraint |

Cost tiers (high/mid/low) are relative and subject to provider pricing changes.
Update `config/settings.yaml → cost_tier_map` when provider pricing changes.

---

## TokenBudgetReport Format

```json
{
  "session_id": "<uuid>",
  "dag_node_count": 4,
  "estimated_tokens": 28000,
  "model_context_limit": 200000,
  "utilization_ratio": 0.14,
  "per_agent_estimates": {
    "OrchestratorAgent": 8000,
    "SecurityAgent": 4000,
    "ExpertAgent": 12000,
    "CoherenceAgent": 4000
  },
  "task_size_tier": "standard",
  "session_cap": 50000,
  "recommendation": "PROCEED",
  "warnings": [],
  "split_suggestions": [],
  "generated_at": "<iso8601>"
}
```

---

## Throttling Rules

TelemetryLogger enforces the following rate limits in addition to the cumulative caps.
Throttling events are always logged; they are never silently suppressed.

**(A) Per-agent rate limit:** if a single agent consumes > 2,000 tokens/minute,
add a 500 ms delay before the next call to that agent.
Log: `{ "event": "AGENT_THROTTLE", "agent_id": "<id>", "rate": "<tokens/min>" }`.

**(B) Session rate limit:** if the session as a whole consumes > 5,000 tokens/minute
across all agents, pause all agent calls for 2 seconds, then resume.
Log: `{ "event": "SESSION_THROTTLE", "rate": "<tokens/min>" }`.

**(C) Repeat invocation limit:** if the same agent is called more than 5 times
within a 60-second window, emit `ESCALATION(PROTOCOL_VIOLATION)` and halt.
This pattern indicates a loop or retry storm and must not be auto-resolved.

---

## Recommendations

| Utilization | Recommendation | Action |
|---|---|---|
| < 0.50 | `PROCEED` — session fits comfortably | No action needed |
| 0.50 – 0.75 | `PROCEED` with monitoring | TelemetryLogger in active watch mode |
| 0.75 – 1.00 | `REVIEW_SCOPE` — consider reducing node count | Evaluate task split or model downgrade |
| > 1.00 | `SPLIT_SESSION` — DAG must be split across sessions | Mandatory; do not proceed without split |

**Additional guidance:**
- Always run `TokenBudgetReport` before Gate 0 confirmation; never skip for "small" tasks
- If `per_agent_estimates` shows a single agent consuming > 40% of budget, flag for review
- For framework meta tasks, use the 200K cap even if the DAG looks small; self-modification
  often triggers recursive file reads that are hard to estimate upfront
- After context compression at 60%, re-run the estimation algorithm on remaining nodes
  and update the live `TokenBudgetReport` in the session state

<!-- v5.1 — expanded from v4 audit -->
