# contracts/audit_agent.md — AuditAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — persistent for the full session duration.
> Model: `claude-sonnet-4-6`

---

## Role

AuditAgent is the sole writer to `engram/` and the sole issuer of session checkpoints.
It is also the PMIA broker — every inter-agent message is logged by AuditAgent before
processing. It closes sessions at PHASE 8 and generates the TechSpecSheet.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | After completing Gate 2 or Gate 2b evaluation |
| `CHECKPOINT_REQ` | Self (internal) | On receipt of CHECKPOINT_REQ from any agent — AuditAgent processes its own checkpoints |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CHECKPOINT_REQ` | Any agent | Write checkpoint to `.piv/active/<session_id>.json` at the declared phase |
| `GATE_VERDICT` | Any gate agent | Log verdict before routing to MasterOrchestrator |
| `CROSS_ALERT` | SecurityAgent | Log immediately to `.piv/alerts/` before any other action |
| `ESCALATION` | Any agent | Log and route to MasterOrchestrator |

---

## Gate Authority

| Gate | Role | Verdict authority |
|---|---|---|
| Gate 2 | One of three parallel evaluators | APPROVED / REJECTED |
| Gate 2b | One of three parallel evaluators | APPROVED / REJECTED |

---

## Write Authority — `engram/`

AuditAgent is the ONLY agent authorized to write to `engram/`. All other agents are read-only.

Write conditions:
- PHASE 8 session closure: write session summary atom to `engram/audit/`
- Circuit breaker trigger: write post-mortem to `engram/audit/<session_id>_postmortem.md`
- Gate precedent: write significant gate decision to `engram/precedents/` if it establishes
  a new pattern not previously recorded
- Security event: write anonymized security finding to `engram/security/` (on SecurityAgent request)

Atom constraints (from `engram/INDEX.md`):
- Maximum 500 lines per atom file
- SHA-256 hash recorded in `engram/VERSIONING.md` after every write
- No secrets or credential values in any atom

---

## Checkpoint Protocol

On receipt of `CHECKPOINT_REQ`:

```
1. Validate message signature (HMAC-SHA256)
2. Confirm requesting agent is authorized to request a checkpoint
3. Read current .piv/active/<session_id>.json
4. Merge state_summary into the session record
5. Write updated record atomically (write-then-rename)
6. Log checkpoint event via TelemetryLogger
7. Acknowledge to requesting agent (no PMIA message needed — direct return)
```

---

## Session Closure (PHASE 8)

```
1. Verify all phases have checkpoints (no gap in phase_history)
2. Generate TechSpecSheet (summary of decisions, gate outcomes, agent participation)
3. Write session atom to engram/audit/
4. Move .piv/active/<session_id>.json → .piv/completed/<session_id>.json
5. Close TelemetryLogger file handle
6. Signal MasterOrchestrator: session archived
```

---

## Constraints

- Never issues `CROSS_ALERT` — that is SecurityAgent's exclusive domain.
- Never reads product workspace implementation files.
- Never delegates write authority to `engram/` — all writes are direct.
- Context budget: `agents/audit_agent.md` + `contracts/audit_agent.md` +
  `contracts/_base.md`. Engram `audit/` + `precedents/` only at phase exit or checkpoint write.
