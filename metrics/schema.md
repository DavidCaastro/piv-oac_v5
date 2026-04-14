# metrics/schema.md — Metrics Schema

**Written by:** `sdk/metrics/collector.py` (TelemetryLogger + MetricsCollector)
**Read by:** EvaluationAgent, AuditAgent, Grafana dashboards

---

## Log File Locations

```
logs/
├── sessions/<session_id>.jsonl   ← all session events (every agent action)
├── gates/<session_id>.jsonl      ← gate verdicts with rationale
└── scores/<session_id>.jsonl     ← EvaluationAgent per-criterion scores
```

`logs/` is gitignored — never versioned. Grafana reads directly from `logs/`.

---

## Canonical Log Line Schema

```json
{
  "timestamp_ms": 1744790781342,
  "timestamp_iso": "2026-04-14T10:23:01.342Z",
  "level": "INFO",
  "session_id": "<uuid>",
  "agent_id": "SecurityAgent",
  "phase": "PHASE_0",
  "action": "injection_scan",
  "outcome": "PASS",
  "tier": 1,
  "duration_ms": 4,
  "tokens_used": 0,
  "detail": {}
}
```

### Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `timestamp_ms` | int | ✅ | Unix epoch milliseconds |
| `timestamp_iso` | str | ✅ | ISO-8601 UTC (same instant as `timestamp_ms`) |
| `level` | str | ✅ | `DEBUG`, `INFO`, `WARN`, `ERROR` |
| `session_id` | str | ✅ | UUID from SessionManager.create() |
| `agent_id` | str | ✅ | Agent identifier from Identity table |
| `phase` | str | ✅ | `PHASE_0` through `PHASE_8` |
| `action` | str | ✅ | Verb describing what happened |
| `outcome` | str | ✅ | `PASS`, `FAIL`, `APPROVED`, `REJECTED`, `OK`, `ERROR` |
| `tier` | int | ✅ | Execution tier: 1, 2, or 3 |
| `duration_ms` | int | ✅ | Wall-clock time for this action |
| `tokens_used` | int | ✅ | LLM tokens consumed (0 for Tier 1) |
| `detail` | dict | ✅ | Action-specific structured payload (may be `{}`) |

---

## Gate Verdict Log Line

Written to `logs/gates/<session_id>.jsonl`:

```json
{
  "timestamp_ms": 1744790800000,
  "timestamp_iso": "2026-04-14T10:23:20.000Z",
  "level": "INFO",
  "session_id": "<uuid>",
  "agent_id": "CoherenceAgent",
  "phase": "GATE_1",
  "action": "gate_verdict",
  "outcome": "APPROVED",
  "tier": 3,
  "duration_ms": 1240,
  "tokens_used": 850,
  "detail": {
    "gate": "GATE_1",
    "rationale": "No semantic conflicts detected between expert subbranches.",
    "checks_passed": ["no_file_overlap", "no_semantic_conflict"],
    "checks_failed": []
  }
}
```

---

## EvaluationAgent Score Log Line

Written to `logs/scores/<session_id>.jsonl`:

```json
{
  "timestamp_ms": 1744790900000,
  "timestamp_iso": "2026-04-14T10:25:00.000Z",
  "level": "INFO",
  "session_id": "<uuid>",
  "agent_id": "EvaluationAgent",
  "phase": "GATE_2B",
  "action": "score_record",
  "outcome": "PASS",
  "tier": 3,
  "duration_ms": 3200,
  "tokens_used": 1420,
  "detail": {
    "expert_id": "expert-1",
    "task_id": "auth-001",
    "dimensions": {
      "FUNC": 0.88,
      "SEC": 0.92,
      "QUAL": 0.85,
      "COH": 0.90,
      "FOOT": 0.95
    },
    "weighted_score": 0.896,
    "early_termination": false,
    "weights": {"FUNC": 0.35, "SEC": 0.25, "QUAL": 0.20, "COH": 0.15, "FOOT": 0.05}
  }
}
```

---

## Agent `_log` Block Format

Every agent response must include a `_log` block. `sdk/core/session.py` strips it
from the visible output and routes it to TelemetryLogger.

```
_log:
  agent_id: CoherenceAgent
  phase: GATE_1
  action: conflict_scan
  outcome: PASS
  tier: 3
  duration_ms: 840
  tokens_used: 620
  detail:
    files_reviewed: 3
    conflicts_found: 0
```

---

## Action Vocabulary (canonical values)

| Action | Used by | Description |
|---|---|---|
| `session_start` | Session | Session initialized |
| `session_close` | AuditAgent | Session closed (COMPLETED/FAILED) |
| `injection_scan` | Vault | Injection scan result |
| `complexity_classify` | ComplexityClassifier | Level 1 or 2 determined |
| `interview_start` | InterviewSession | PHASE 0.1 began |
| `spec_write` | SpecWriter | Spec file written |
| `dag_build` | DAGBuilder | DAG validated and built |
| `gate_verdict` | Any gate agent | Gate outcome |
| `checkpoint_req` | SpecialistAgent | Checkpoint sent to AuditAgent |
| `fragmentation` | SecurityAgent | Context saturation sub-agent spawn |
| `escalation` | Any agent | ESCALATION message emitted |
| `engram_write` | AuditAgent | Atom written to engram/ |
| `engram_prune` | AuditAgent | Atom removed per retention policy |
| `circuit_breaker_triggered` | GateEvaluator | 3 consecutive rejections |
