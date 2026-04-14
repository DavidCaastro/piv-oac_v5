# skills/metrics-collection.md — Metrics Collection

## When to Load

When configuring the `_log` block format or extending TelemetryLogger.

## Agent `_log` Block (every agent response)

Every agent response must include a `_log` block at the end.
`sdk/core/session.py` strips it and routes to TelemetryLogger.record().

```yaml
_log:
  agent_id: <agent-id>
  phase: PHASE_N
  action: <action-verb>
  outcome: PASS | FAIL | APPROVED | REJECTED | OK | ERROR
  tier: 1 | 2 | 3
  duration_ms: <integer>
  tokens_used: <integer>
  detail:
    <key>: <value>   # action-specific
```

## Canonical Actions

```
session_start | session_close | injection_scan | complexity_classify
interview_start | spec_write | dag_build | gate_verdict
checkpoint_req | fragmentation | escalation | engram_write
engram_prune | circuit_breaker_triggered
```

## MetricsCollector (EvaluationAgent)

```python
from sdk.metrics import MetricsCollector

collector = MetricsCollector(session_id, log_dir=Path("logs"))
collector.record({
    "level": "INFO", "agent_id": "EvaluationAgent",
    "phase": "GATE_2B", "action": "score_record",
    "outcome": "PASS", "tier": 3,
    "duration_ms": 3200, "tokens_used": 1420,
    "detail": {"weighted_score": 0.896, "dimensions": {...}}
})
collector.close()
```

## Multiple TelemetryLogger Instances

One instance per log type per session:
- `sessions/` — all events
- `gates/` — gate verdicts only
- `scores/` — EvaluationAgent scores only

All use the same `record()` / `close()` interface.

## OTEL Fire-and-Forget

```python
# Automatic — no configuration needed
# TelemetryLogger._check_otel_collector() is called once at __init__
# If reachable: async thread started per record
# If unreachable: silently skipped — file log is authoritative
```
