# skills/session-continuity.md — Session Continuity

## When to Load

When resuming an interrupted session or handling context expiry mid-session.

## State Locations

```
.piv/active/<session_id>.json     ← running session
.piv/completed/<session_id>.json  ← closed cleanly
.piv/failed/<session_id>.json     ← circuit breaker or crash
.piv/checkpoints/<session_id>.jsonl ← append-only event log
```

## Session State Schema (JSON)

```json
{
  "session_id": "<uuid>",
  "status": "active",
  "objective": "...",
  "provider": "anthropic",
  "created_at": "2026-04-14T10:00:00Z",
  "updated_at": "2026-04-14T10:23:01Z",
  "phase": "PHASE_5",
  "consecutive_rejections": 0,
  "dag": { ... }
}
```

## Resume Protocol

1. `piv-oac init --provider=X` detects `.piv/active/` files
2. Warns user: "Found N interrupted session(s)"
3. User chooses: resume or start clean
4. Resume: load session JSON → restore phase → continue from last checkpoint
5. Clean: move interrupted session to `.piv/failed/` → start new

## Checkpoint Frequency

Specialist Agents: checkpoint at every logical unit commit.
Control agents: checkpoint at each gate verdict.
ExecutionAuditor: reads checkpoints every N intervals (default: 3).

## Session Closure (PHASE 8)

```
AuditAgent:
  1. Write TechSpecSheet to engram/audit/<session_id>/spec.md
  2. Write session record to engram/audit/<session_id>/record.json
  3. Move .piv/active/<id>.json → .piv/completed/<id>.json
  4. TelemetryLogger.close()
  5. Prune engram per retention policy
```
