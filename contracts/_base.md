# contracts/_base.md — PMIA v5.0 Base Protocol

> PMIA: Protocol for Multi-agent Interaction and Arbitration, version 5.0.
> This file is mandatory for every agent. It is always loaded at instantiation.
> No agent contract may override or weaken any rule defined here.
> Agent contracts may only ADD role-specific constraints on top of this base.

---

## 1. Protocol Identity

| Field | Value |
|---|---|
| Protocol name | PMIA — Protocol for Multi-agent Interaction and Arbitration |
| Version | 5.0 |
| Baseline | New versioning baseline from v5.0 (logic inherited from v4.0) |
| Broker | AuditAgent — all messages are logged by AuditAgent before processing |
| Transport | In-process (same session context); structured dict payload |

---

## 2. Message Types

Every inter-agent message must be one of these four types. No custom types allowed.

| Type | Direction | Purpose | Max tokens |
|---|---|---|---|
| `GATE_VERDICT` | Gate agent → MasterOrchestrator | Approve or reject at a gate | 300 |
| `ESCALATION` | Any agent → level above | Context saturation or unresolvable conflict | 300 |
| `CROSS_ALERT` | SecurityAgent → any | Security issue requiring immediate attention | 300 |
| `CHECKPOINT_REQ` | Any agent → AuditAgent | Request a checkpoint write to `.piv/` | 300 |

### GATE_VERDICT schema

```json
{
  "type": "GATE_VERDICT",
  "gate": "Gate0 | Gate1 | Gate2 | Gate2b | Gate3",
  "verdict": "APPROVED | REJECTED | BLOCKED_BY_TOOL",
  "agent_id": "<issuing agent>",
  "session_id": "<uuid>",
  "rationale": "<reason — max 200 tokens>",
  "timestamp_ms": 1744790781342
}
```

### ESCALATION schema

```json
{
  "type": "ESCALATION",
  "reason": "CONTEXT_SATURATION | UNRESOLVABLE_CONFLICT | PROTOCOL_VIOLATION",
  "agent_id": "<issuing agent>",
  "session_id": "<uuid>",
  "context": "<description — max 200 tokens>",
  "timestamp_ms": 1744790781342
}
```

### CROSS_ALERT schema

```json
{
  "type": "CROSS_ALERT",
  "severity": "CRITICAL | HIGH | MEDIUM",
  "agent_id": "SecurityAgent",
  "session_id": "<uuid>",
  "description": "<threat description — max 200 tokens>",
  "action_required": "<what must happen next>",
  "timestamp_ms": 1744790781342
}
```

### CHECKPOINT_REQ schema

```json
{
  "type": "CHECKPOINT_REQ",
  "phase": "PHASE_0 | PHASE_1 | ... | PHASE_8",
  "agent_id": "<requesting agent>",
  "session_id": "<uuid>",
  "state_summary": "<what to checkpoint — max 150 tokens>",
  "timestamp_ms": 1744790781342
}
```

---

## 3. Message Constraints

| Constraint | Rule |
|---|---|
| Max message size | 300 tokens — hard limit, enforced by `sdk/core/session.py` |
| Signature | HMAC-SHA256 — key sourced from Vault, never exposed in context |
| Malformed message retry | Maximum 2 attempts, then escalate as `PROTOCOL_VIOLATION` |
| No secrets in payload | Credentials, tokens, and keys are strictly prohibited in any field |
| Broker logging | AuditAgent logs every message before it is processed — no exceptions |
| No direct agent-to-agent | All messages route through the session broker, not point-to-point |

---

## 4. Gate Invariants

These invariants are defined here and cannot be modified by any agent contract.
Any contract that appears to conflict with these invariants is invalid.

| Invariant | Detail |
|---|---|
| **Gate 2 before worktree** | No worktree is created without a `GATE_VERDICT: APPROVED` for Gate 2 |
| **Gate 3 requires human** | `main` is unreachable by any automated process. Gate 3 requires explicit human confirmation after ComplianceAgent checklist |
| **SecurityAgent veto** | A `CROSS_ALERT` from SecurityAgent overrides any `GATE_VERDICT: APPROVED` at any gate, at any phase |
| **Gate 3 human signal** | No workflow, script, or agent can issue the Gate 3 merge signal — only a human pressing the merge button |
| **Extend, never weaken** | Agent contracts may add evaluation criteria to a gate. They may never remove or lower the bar of an invariant defined in this file |
| **_base.md is the authority** | In any conflict between this file and an agent contract, this file wins |

---

## 5. Circuit Breaker

Three consecutive `GATE_VERDICT: REJECTED` messages at the same gate trigger the circuit breaker:

```
MAX_GATE_REJECTIONS = 3

On trigger:
  1. MasterOrchestrator halts all active agents
  2. Session moved to .piv/failed/<session_id>.json
  3. AuditAgent writes post-mortem to engram/audit/<session_id>_postmortem.md
  4. All active worktrees listed in .piv/failed/ for manual review
  5. No automatic retry — human intervention required
```

---

## 6. Agent Response Structure

Every agent response must include a `_log` block. This is mandatory regardless of
whether the response contains a gate verdict, a result, or an error.

```json
{
  "result": {},
  "_log": {
    "timestamp_ms": 1744790781342,
    "timestamp_iso": "2026-04-14T10:23:01.342Z",
    "session_id": "<uuid>",
    "agent_id": "<agent>",
    "phase": "PHASE_N",
    "action": "<what was done>",
    "outcome": "PASS | FAIL | VETO | BLOCKED | ESCALATED",
    "tier": 1,
    "duration_ms": 0,
    "tokens_used": 0,
    "detail": {}
  }
}
```

`sdk/core/session.py` extracts `_log` and routes it to `TelemetryLogger` before
passing `result` to the next agent. Agents never write to `logs/` directly.

---

## 7. Execution Phases Reference

| Phase | Name | Key agents |
|---|---|---|
| PHASE 0 | Intent validation + injection scan | SecurityAgent, MasterOrchestrator |
| PHASE 1 | DAG construction + token budget | MasterOrchestrator, LogisticsAgent |
| PHASE 2 | Control environment instantiation | Security, Audit, Coherence, Standards, Compliance |
| PHASE 3 | Domain planning | Domain Orchestrators |
| PHASE 4 | Plan review (Gate 2) | Security + Audit + Coherence |
| PHASE 5 | Parallel specialist execution | Specialist Agents, EvaluationAgent, CoherenceAgent |
| PHASE 6 | Two-level merge (Gate 1 + Gate 2b) | CoherenceAgent, SecurityAgent, StandardsAgent |
| PHASE 7 | Documentation | DocumentationAgent |
| PHASE 8 | Session closure + engram update | AuditAgent |
