# skills/observability.md — Observability

## When to Load

When configuring logging, OTEL, or Grafana stack for a session.

## Log Architecture

Primary: `logs/<type>/<session_id>.jsonl` — sync write, flush after every line.
Secondary: OTEL Collector on `:4317` — async, fire-and-forget.

File log is always sufficient. OTEL is optional enhancement for capable machines.

## TelemetryLogger Usage

```python
logger = TelemetryLogger(session_id, log_dir=Path("logs"))
logger.record({
    "level": "INFO", "agent_id": "X", "phase": "PHASE_N",
    "action": "...", "outcome": "...", "tier": 1,
    "duration_ms": 0, "tokens_used": 0, "detail": {}
})
logger.close()  # called at PHASE 8 only
```

One file handle per session — no per-event open/close.

## Grafana Stack (optional)

```bash
piv observe:start   # docker compose up -d
piv observe:stop    # docker compose down
piv observe:logs    # tail -f logs/sessions/<latest>.jsonl
```

Stack: Loki + Tempo + Grafana + OTEL Collector. ~470MB RAM total.
Resource-limited — safe on mid-range machines. Not started automatically.

## OTEL Check (Tier 1)

```python
import socket
def check_otel() -> bool:
    try:
        with socket.create_connection(("localhost", 4317), timeout=1): return True
    except OSError: return False
```

## Log Levels

| Level | Use |
|---|---|
| `INFO` | Normal operation, gate verdicts, phase transitions |
| `WARN` | Degraded mode, missing optional component |
| `ERROR` | Unrecoverable error (ESCALATION follows) |
| `DEBUG` | Verbose — dev/test only, not in production logs |
