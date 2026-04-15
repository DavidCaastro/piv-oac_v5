# skills/observability.md — Observability

## When to Load

When configuring logging, OTEL, or Grafana stack for a session. Load this skill when:
- A session is initializing its TelemetryLogger for the first time.
- An agent reports a WARN or ERROR that requires structured trace context.
- The Grafana stack (`piv observe:start`) is being configured or debugged.
- Gate 0 bootstrap validation checks OTEL availability.

---

## Why OpenTelemetry

PIV/OAC v5 uses OpenTelemetry (OTEL) as its observability standard rather than alternatives.
The rationale per CNCF alignment:

1. **Vendor-neutral collector**: A single OTEL Collector on `:4317` receives traces, metrics,
   and logs from all agents. Switching backends (Grafana, Datadog, Jaeger) requires only
   an exporter config change — no instrumentation changes in `sdk/core/telemetry.py`.
   Prometheus standalone cannot carry traces; Datadog agent requires proprietary SDK calls
   embedded in agent code.

2. **Unified context propagation**: OTEL W3C TraceContext headers allow parent/child span
   relationships to be preserved across agent boundaries over PMIA messages. Custom logging
   solutions (e.g., bare `logging.getLogger`) lose causal chain when a CROSS_ALERT or
   ESCALATION crosses agent boundaries.

3. **Semantic conventions**: OTEL defines canonical attribute names (`session.id`,
   `agent.id`, `phase.name`) that map directly to PIV/OAC's log schema. Grafana dashboards
   can query by these attributes without per-deployment field mapping.

4. **Fire-and-forget async path**: The OTEL SDK's `BatchSpanProcessor` buffers and exports
   asynchronously, imposing <1 ms overhead on the hot path (LLM call initiation). A Datadog
   agent or custom HTTP sink would block agent execution waiting for network ACK.

---

## Log Architecture

PIV/OAC uses three levels of log infrastructure. Each level is additive — lower levels are
always sufficient; higher levels add query capability at the cost of resource usage.

### Level 1 — Structured JSON (always active)

```
logs/
  sessions/<session_id>.jsonl     ← primary session log, one JSON object per line
  gates/<session_id>_gates.jsonl  ← gate verdicts only (GATE_VERDICT messages)
  errors/<session_id>_errors.jsonl← ERROR-level events only
```

- Written synchronously with `flush()` after every line. No buffering.
- File handle opened once at session start, closed at PHASE 8 via `logger.close()`.
- Every record is a self-contained JSON object — parseable without context.
- **Latency budget**: sync write + flush must complete in ≤2 ms. If OS write latency
  exceeds 5 ms (e.g., networked filesystem), TelemetryLogger logs a WARN and continues.

### Level 2 — OTEL Collector (optional, async)

```
OTEL Collector on localhost:4317 (gRPC) or localhost:4318 (HTTP/protobuf)
  ↑ receives from: sdk/core/telemetry.py BatchSpanProcessor
  ↓ exports to:    Loki (logs), Tempo (traces), Prometheus (metrics)
```

- All OTEL export is fire-and-forget. A collector outage does not block session execution.
- Activated automatically when `check_otel()` returns `True` at Gate 0.
- **Latency budget**: OTEL export must not add more than 1 ms to agent hot path.
  BatchSpanProcessor flush interval: 5 000 ms, max batch size: 512 spans.

### Level 3 — Grafana Backend (optional, query layer)

```
Grafana on localhost:3000
  ← Loki  datasource: structured JSON log queries
  ← Tempo datasource: distributed trace view (span waterfall)
  ← Prometheus datasource: time-series metrics panels
```

- Stack consumes ~470 MB RAM. Started explicitly via `piv observe:start`.
- Not started automatically — safe on machines with ≥8 GB RAM.
- Query latency for a 1-hour session log in Loki: typically <500 ms.

---

## Core Metrics (6 Canonical)

These six metrics are emitted by `TelemetryLogger` on every session. All are queryable
in Grafana and exported as OTEL metrics if the collector is reachable.

| Metric | Type | Unit | Description |
|---|---|---|---|
| `session_duration_ms` | Gauge | ms | Wall-clock time from PHASE 0 start to PHASE 8 close |
| `tokens_consumed` | Counter | tokens | Cumulative tokens across all LLM calls in the session |
| `gate_verdicts_total` | Counter | count | APPROVED / REJECTED / CONDITIONAL verdicts per gate |
| `expert_invocations` | Counter | count | Number of ExpertAgent (specialist_agent) calls dispatched |
| `circuit_breaker_trips` | Counter | count | Provider circuit-breaker open events (per provider label) |
| `phase_durations[]` | Histogram | ms | Duration per PHASE 0–8; array index = phase number |

**Emission pattern** — each metric is recorded as an attribute on the session close span:

```python
logger.record({
    "level": "INFO",
    "agent_id": "TelemetryLogger",
    "phase": "PHASE_8",
    "action": "session_close",
    "outcome": "COMPLETE",
    "tier": 1,
    "duration_ms": session_duration_ms,
    "tokens_used": tokens_consumed,
    "detail": {
        "gate_verdicts_total": {"APPROVED": 3, "REJECTED": 0, "CONDITIONAL": 1},
        "expert_invocations": 2,
        "circuit_breaker_trips": 0,
        "phase_durations_ms": [120, 340, 88, 0, 1200, 450, 890, 210, 15],
    },
})
```

---

## Trace Structure

### Span Naming Convention

All spans emitted by PIV/OAC follow the pattern:

```
piv.<phase>.<operation>
```

Examples:
- `piv.phase0.objective_scan` — SecurityAgent injection scan at PHASE 0
- `piv.phase1.dag_build` — OrchestratorAgent DAG construction
- `piv.phase4.gate2_eval` — Gate 2 multi-agent evaluation
- `piv.phase5.llm_call` — ExpertAgent LLM invocation (hot path)
- `piv.phase8.session_close` — TelemetryLogger final flush

### Parent/Child Span Hierarchy

```
piv.session (root)
├── piv.phase0.objective_scan         [SecurityAgent]
├── piv.phase1.dag_build              [OrchestratorAgent]
│   └── piv.phase1.dag_validate       [CoherenceAgent]
├── piv.phase4.gate2_eval             [Gate evaluators]
│   ├── piv.phase4.gate2_eval.security
│   ├── piv.phase4.gate2_eval.coherence
│   └── piv.phase4.gate2_eval.standards
└── piv.phase5.llm_call               [ExpertAgent, repeating]
    └── piv.phase5.injection_scan     [SecurityAgent sub-span]
```

### Trace Context Propagation

When a PMIA message crosses agent boundaries (e.g., ESCALATION from SecurityAgent to
OrchestratorAgent), the sending agent serializes the current span context into the
message envelope:

```json
{
  "pmia_type": "ESCALATION",
  "trace_context": {
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "tracestate": "piv=phase5"
  },
  "payload": { ... }
}
```

The receiving agent extracts `traceparent` and creates a child span, preserving causal
chain across the PMIA boundary.

---

## TelemetryLogger Integration

### SDK Usage Pattern

```python
from pathlib import Path
from sdk.core.telemetry import TelemetryLogger

# Instantiated once at session start (PHASE 0) by AsyncSession
logger = TelemetryLogger(session_id="abc123", log_dir=Path("logs"))

# Standard record — used by all agents
logger.record({
    "level": "INFO",          # ERROR | WARN | INFO | DEBUG
    "agent_id": "SecurityAgent",
    "phase": "PHASE_0",
    "action": "injection_scan",
    "outcome": "CLEAN",
    "tier": 1,                # 1 = Tier1 (always), 2 = conditional
    "duration_ms": 14,
    "tokens_used": 0,
    "detail": {"scan_target": "objective", "patterns_checked": 47}
})

# Session close — called at PHASE 8 only, never earlier
logger.close()
```

- One file handle per session — never open/close per event.
- `detail` is a free-form dict; keep keys consistent per action type for Loki queries.
- `tier` field maps to bootstrap validation tiers: `1` = Tier 1 (must pass), `2` = Tier 2.

### Fire-and-Forget OTEL Export Pattern

OTEL export is non-blocking. The `TelemetryLogger` submits spans to a
`BatchSpanProcessor` which flushes asynchronously:

```python
# Internal to TelemetryLogger — agents do not call this directly
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
```

### OTEL Exporter Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | gRPC collector endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` | `grpc` or `http/protobuf` |
| `OTEL_SERVICE_NAME` | `piv-oac` | Service name shown in Tempo/Jaeger |
| `OTEL_SDK_DISABLED` | `false` | Set `true` to disable all OTEL export |

If `OTEL_EXPORTER_OTLP_ENDPOINT` is not set, the TelemetryLogger falls back to
file-only logging (Level 1). No error is raised — this is normal for offline runs.

---

## Grafana Dashboard (6 Panels)

The PIV/OAC Grafana dashboard (`observability/grafana/dashboard.json`) contains six panels.
Each panel maps to one or more of the canonical metrics above.

### Panel 1 — Session Timeline

- **Type**: Timeline / Gantt
- **Source**: Tempo (traces)
- **Query**: Root span `piv.session`, child spans by phase
- **Use**: Visually identify which phase consumed the most wall-clock time.
- **Alert threshold**: Any single phase exceeding 10 min triggers WARN in panel.

### Panel 2 — Token Budget

- **Type**: Gauge + time-series
- **Source**: Loki (`tokens_used` field, cumulative sum)
- **Query**: `sum(tokens_used) by (session_id)` over session window
- **Use**: Track token consumption rate; detect runaway phases before budget exhaustion.
- **Alert threshold**: 90% of session token budget → pre-veto warning (see Alerts).

### Panel 3 — Gate Verdicts

- **Type**: Bar chart (stacked APPROVED / REJECTED / CONDITIONAL)
- **Source**: Loki (`action = "gate_verdict"`)
- **Query**: `count_over_time({action="gate_verdict"} [1h])` grouped by outcome
- **Use**: Identify gates with high CONDITIONAL or REJECTED rates across sessions.
- **Alert threshold**: Gate pass rate <95% over 24 h → reliability alert.

### Panel 4 — Expert Load

- **Type**: Time-series
- **Source**: Loki (`action = "expert_invocation"`)
- **Query**: `rate({action="expert_invocation"} [5m])` per session
- **Use**: Detect expert agent overload; correlate with phase_durations for bottlenecks.

### Panel 5 — Circuit Breaker Rate

- **Type**: Stat + time-series
- **Source**: Loki (`action = "circuit_breaker_trip"`)
- **Query**: `count_over_time({action="circuit_breaker_trip"} [1h])` per provider
- **Use**: Identify flapping LLM providers; trigger provider routing review.
- **Alert threshold**: >3 trips per provider per hour → WARN to OrchestratorAgent.

### Panel 6 — Phase Duration Heatmap

- **Type**: Heatmap
- **Source**: Prometheus (`phase_durations_ms` histogram)
- **Query**: `histogram_quantile(0.95, phase_durations_ms)` per phase label
- **Use**: Compare p95 phase durations across sessions; detect regressions after
  framework changes.

---

## Critical Alerts (4)

These four alerts are defined in `observability/grafana/alerts.json`. When triggered,
they emit a WARN or ERROR into the session log AND (if OTEL is active) create a root span
annotation visible in Tempo.

### Alert 1 — Pre-Veto Warning (90% Token Budget)

- **Trigger**: `tokens_consumed / session_token_budget >= 0.90`
- **Check interval**: Every 30 seconds during PHASE 5 (execution).
- **Action**: TelemetryLogger emits `level=WARN, action="pre_veto_warning"`.
  OrchestratorAgent receives CHECKPOINT_REQ from AuditAgent requesting scope reduction.
- **Escalation**: If budget reaches 95%, OrchestratorAgent issues GATE_VERDICT(CONDITIONAL)
  before proceeding to PHASE 6.

### Alert 2 — Deadlock Detection (No Progress 5+ Minutes)

- **Trigger**: No `logger.record()` call with `phase` matching the current active phase
  for ≥5 minutes wall-clock time.
- **Check interval**: Background watchdog in AsyncSession, 60-second poll.
- **Action**: AsyncSession emits `level=ERROR, action="deadlock_suspected"`.
  ESCALATION broadcast to all agents. If no recovery in 2 minutes, session is terminated
  with outcome `ABORTED_DEADLOCK`.

### Alert 3 — Budget Exceeded

- **Trigger**: `tokens_consumed > session_token_budget` (hard limit).
- **Check interval**: On every `logger.record()` call that includes `tokens_used > 0`.
- **Action**: Immediate `level=ERROR, action="budget_exceeded"`. Current phase is halted.
  OrchestratorAgent issues GATE_VERDICT(REJECTED) for the active gate. Session proceeds
  to PHASE 7 (documentation) with partial results, then PHASE 8 (close).

### Alert 4 — Reliability Drop (<95% Gate Pass Rate)

- **Trigger**: Rolling 24-hour gate pass rate (APPROVED / total verdicts) < 0.95,
  computed across all sessions in `logs/gates/`.
- **Check interval**: Evaluated by `piv observe:health` CLI command (manual or cron).
- **Action**: WARN written to `logs/errors/reliability.jsonl`. Framework operator is
  notified to review gate evaluator model assignments and contract thresholds.

---

## Log Levels

Every `logger.record()` call must specify one of four levels. Misuse of levels degrades
Grafana alert accuracy — use the definitions below strictly.

### ERROR

Unrecoverable condition within an agent or the session. An ESCALATION PMIA message
**must** follow within the same phase turn. Session outcome will be `FAILED` or
`ABORTED_*`.

Examples by agent:
- `SecurityAgent`: `"action": "injection_detected"` — objective or spec file contains
  prompt injection pattern; session halted.
- `OrchestratorAgent`: `"action": "dag_cycle_detected"` — DAG build produced a cycle;
  PHASE 1 cannot complete.
- `AsyncSession`: `"action": "budget_exceeded"` — token hard limit crossed.
- `AuditAgent`: `"action": "audit_write_failed"` — cannot persist to `engram/audit/`;
  session integrity at risk.

### WARN

Degraded operation — session continues but with reduced capability or a flag for
post-session review. No ESCALATION required, but AuditAgent records the event.

Examples by agent:
- `TelemetryLogger`: `"action": "otel_unavailable"` — collector not reachable; falling
  back to file-only logging.
- `SecurityAgent`: `"action": "scan_timeout"` — injection scan exceeded 500 ms; scan
  result treated as INCONCLUSIVE (conservative: proceed with caution flag).
- `OrchestratorAgent`: `"action": "pre_veto_warning"` — 90% token budget consumed.
- `EvaluationAgent`: `"action": "score_borderline"` — evaluation score 0.78–0.80;
  within threshold but logged for trend analysis.

### INFO

Normal operation. Every phase transition, gate verdict, and agent action produces an
INFO record. These are the primary records for session reconstruction and audit.

Examples by agent:
- `OrchestratorAgent`: `"action": "phase_transition", "detail": {"from": "PHASE_1", "to": "PHASE_2"}`
- `SecurityAgent`: `"action": "injection_scan", "outcome": "CLEAN"`
- `ComplianceAgent`: `"action": "gate3_checklist_complete", "outcome": "APPROVED"`
- `AuditAgent`: `"action": "engram_write", "detail": {"file": "engram/core/session_abc123.md"}`

### DEBUG

Verbose internal state — enabled only in development or test runs via
`OTEL_LOG_LEVEL=DEBUG` environment variable. Never written to production session logs.

Examples by agent:
- `CoherenceAgent`: `"action": "coherence_check_step"` emitted for each of N spec items.
- `FrameworkLoader`: `"action": "skill_hash_verified"` for each skill loaded.
- `DAGBuilder`: `"action": "node_added"` for each task node during DAG construction.
- `BatchSpanProcessor`: internal flush cycle timings.

---

## OTEL Check (Tier 1)

This check runs at Gate 0 (bootstrap validation, Tier 1). It determines whether the OTEL
Collector is reachable and sets `otel_available` in session state. All subsequent OTEL
export decisions branch on this flag.

```python
import socket

def check_otel() -> bool:
    """Returns True if OTEL Collector is reachable on localhost:4317.

    Called once at Gate 0. Result stored in session state as otel_available.
    A False result is not a BLOCKER — file-only logging is always sufficient.
    """
    try:
        with socket.create_connection(("localhost", 4317), timeout=1):
            return True
    except OSError:
        return False
```

**Behavior by result:**

| Result | Session behavior |
|---|---|
| `True` | BatchSpanProcessor activated; metrics exported to Prometheus; traces to Tempo |
| `False` | WARN logged: `"otel_unavailable"`; file-only logging active; Grafana dashboards will show no data |

**Environment override**: If `OTEL_SDK_DISABLED=true` is set, `check_otel()` is skipped
and the result is treated as `False` regardless of collector state. Use this for
air-gapped or resource-constrained runs.

**Stack check** — to verify all three Grafana stack components are reachable:

```bash
piv observe:start          # docker compose up -d (Loki + Tempo + Grafana + Collector)
piv observe:logs           # tail -f logs/sessions/<latest>.jsonl
piv observe:health         # check all four stack ports: 4317, 3100, 3200, 3000
piv observe:stop           # docker compose down
```

<!-- v5.1 — expanded from v4 audit -->
