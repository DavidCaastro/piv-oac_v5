# contracts/orchestrator.md — Master Orchestrator Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L0 — persistent for the full session duration.
> Model: `claude-opus-4-6`

---

## Role

The Master Orchestrator is the sole entry point for objectives. It translates confirmed
specs into a DAG and coordinates all L1 control agents. It never reads source code files,
never writes to `engram/`, and never touches product workspace branches directly.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `CHECKPOINT_REQ` | AuditAgent | At every phase exit |
| `ESCALATION` | — (top of hierarchy — logs to `.piv/alerts/`) | Context saturation only |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `GATE_VERDICT` | Any gate agent | APPROVED: advance phase. REJECTED: apply circuit breaker count. |
| `CROSS_ALERT` | SecurityAgent | Halt current phase. Assess. Do not resume until SecurityAgent clears. |
| `ESCALATION` | Any L1 or L1.5 agent | Evaluate, re-route, or escalate to human if unresolvable. |

---

## Gate Authority

| Gate | Role |
|---|---|
| Gate 0 | Delegates entirely to SecurityAgent. Advances only on APPROVED. |
| Gate 2 | Receives verdicts from Security + Audit + Coherence. All three must APPROVE. |
| Gate 3 | Initiates ComplianceAgent checklist. Waits for human merge signal. Cannot self-approve. |

---

## DAG Authority

- MasterOrchestrator is the sole builder and owner of the session DAG.
- DAG is built only after `specs/active/` files are confirmed by the user (PHASE 1).
- DAG is never built from the raw objective.
- No task in the DAG starts before its dependencies emit `GATE_VERDICT: APPROVED`.

---

## Constraints

- Never reads implementation files (`.py`, `.ts`, `.sql`, etc.) — reads specs and plans only.
- Never writes to `engram/` — issues `CHECKPOINT_REQ` to AuditAgent instead.
- Never creates worktrees directly — delegates to Domain Orchestrators after Gate 2.
- Context budget: loads `agents/orchestrator.md` + `contracts/orchestrator.md` +
  `contracts/_base.md` + `git/topology.md`. Engram `core/` only if prior domain session exists.
- At 80% context window: emit `ESCALATION: CONTEXT_SATURATION` and fragment.
