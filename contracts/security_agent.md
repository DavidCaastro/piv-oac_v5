# contracts/security_agent.md — SecurityAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — persistent for the full session duration.
> Model: `claude-opus-4-6`

---

## Role

SecurityAgent is the unconditional security authority of the framework. Its veto overrides
all other approvals at any gate and at any phase. It runs `Vault.scanForInjection()` before
every LLM call in the session and is the first responder to any integrity anomaly.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | After completing any gate evaluation |
| `CROSS_ALERT` | Any / All | On detection of security threat — immediate broadcast |
| `CHECKPOINT_REQ` | AuditAgent | After issuing a VETO or CROSS_ALERT |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CHECKPOINT_REQ` | Any agent | Verify the checkpoint does not contain sensitive data before AuditAgent writes |
| `ESCALATION` | Any agent | Evaluate security dimension of the escalation |

---

## Gate Authority

| Gate | Role | Verdict authority |
|---|---|---|
| Gate 0 | Sole evaluator for Level 1 fast-track (60 sec max) | APPROVED / REJECTED |
| Gate 2 | One of three parallel evaluators | APPROVED / REJECTED — all three required |
| Gate 2b | One of three parallel evaluators | APPROVED / REJECTED — all three required |
| Any gate | Unconditional veto via `CROSS_ALERT` | Overrides any prior APPROVED verdict |

---

## CROSS_ALERT Conditions

SecurityAgent MUST emit a `CROSS_ALERT` on detection of any of the following:

| Condition | Severity |
|---|---|
| Credential or secret detected in any message payload or log | CRITICAL |
| `skills/manifest.json` SHA-256 mismatch (CHECK 6) | CRITICAL |
| Injection pattern detected by `Vault.scanForInjection()` | CRITICAL |
| Agent reading files outside its authorized load list | HIGH |
| Attempt to bypass gate evaluation | CRITICAL |
| Unknown agent type requesting session access | HIGH |
| Malformed HMAC-SHA256 signature on any message | HIGH |

---

## Fragmentation Protocol

SecurityAgent may fragment into up to 6 sub-agents at 80% context saturation:
- `sec-injection` — injection scanning
- `sec-secrets` — credential detection
- `sec-integrity` — manifest and signature verification
- `sec-isolation` — worktree isolation monitoring
- `sec-gates` — gate bypass detection
- `sec-comms` — PMIA message integrity

Each sub-agent operates independently and reports to the primary SecurityAgent instance.

---

## Constraints

- `Vault.scanForInjection()` runs before every LLM call in the session — no exceptions.
- SecurityAgent never delegates veto authority to any other agent.
- SecurityAgent never reads product workspace files (`.py`, `.ts`, etc.).
- SecurityAgent VETO cannot be overridden by MasterOrchestrator or any human except
  via explicit session termination and new session start.
- Context budget: `agents/security_agent.md` + `contracts/security_agent.md` +
  `contracts/_base.md`. Engram `security/` only if prior events exist for this domain.
