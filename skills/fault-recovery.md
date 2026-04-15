# skills/fault-recovery.md — Fault Recovery

## When to Load

Load when: handling any agent failure, timeout, malformed output, or circuit breaker event.
Loaded by: OrchestratorAgent, AuditAgent.
NOT required for: routine gate evaluations with no failure condition.

---

## Fault Classification (7 Types)

| ID | Fault Type | Definition |
|---|---|---|
| F-01 | `AGENT_TIMEOUT` | Agent invocation exceeded the configured time limit (default 300s). No response received within window. |
| F-02 | `MALFORMED_OUTPUT` | Agent returned output that fails schema validation. Required fields missing, type mismatch, or unparseable JSON. |
| F-03 | `SECURITY_VETO` | SecurityAgent issued `GATE_VERDICT(REJECTED)` or `CROSS_ALERT`. Operation is explicitly prohibited. |
| F-04 | `CONTEXT_OVERFLOW` | Agent hit 100% of its token budget. Results in `ESCALATION(reason=CONTEXT_SATURATION)`. |
| F-05 | `WORKTREE_CONFLICT` | File overlap detected between two or more parallel expert nodes writing to the same path. |
| F-06 | `GATE_DEADLOCK` | Two agents are waiting on each other's gate verdict. Neither can proceed without the other's approval. |
| F-07 | `EXTERNAL_API_FAILURE` | Provider API returned 5xx status, connection timeout, or rate limit (429). No usable response received. |

---

## Recovery Strategy per Fault Type

| Fault Type | Immediate Action | Recovery Action | Escalate If |
|---|---|---|---|
| `AGENT_TIMEOUT` | Stop the agent invocation. Log timeout event with elapsed time. | Retry once with 2× the original timeout limit. | Second timeout occurs — emit `ESCALATION(UNRESOLVABLE_CONFLICT)`. |
| `MALFORMED_OUTPUT` | Log schema violation with diff of expected vs. received structure. | Retry with explicit format reminder injected into system prompt. | 3 consecutive retries all return malformed output. |
| `SECURITY_VETO` | Halt the affected node immediately. Do NOT retry. | Log full veto context to `engram/security/<session_id>/`. Surface rejection reason to user verbatim. | Always escalate to OrchestratorAgent for review. Blocked node marked `PERMANENTLY_REJECTED`. |
| `CONTEXT_OVERFLOW` | Emit `CHECKPOINT_REQ` immediately before any further action. | Apply 60% context compression (drop intermediate reasoning, keep conclusions). Retry compressed prompt. | If compressed prompt still overflows: split the node into two smaller scopes. |
| `WORKTREE_CONFLICT` | Identify all overlapping file paths from `_claimed_files` registry. | Re-assign conflicting files to the single agent with semantic ownership. Log `CROSS_ALERT(severity=MEDIUM)`. | If ownership is ambiguous and re-assignment fails: create a merge node. |
| `GATE_DEADLOCK` | Detect via timeout: if no verdict received within 120s, deadlock is assumed. | Force-serialize the agent pair — arbitrarily pick agent A to go first, then agent B. | Log `CROSS_ALERT(severity=HIGH)` on every gate deadlock regardless of outcome. |
| `EXTERNAL_API_FAILURE` | Log failure with HTTP status code, provider, and timestamp. | Retry with exponential backoff (see protocol below). After 3 retries, switch provider per fallback chain. | If all providers in the fallback chain fail: `ESCALATION(UNRESOLVABLE_CONFLICT)`. |

---

## Exponential Backoff Protocol

Applied to `EXTERNAL_API_FAILURE` retries.

| Attempt | Wait Before Retry | Notes |
|---|---|---|
| 1 | Immediate (0s) | First attempt, no delay. |
| 2 | 5 seconds + jitter | Add `random(0, 2)` seconds to avoid thundering herd. |
| 3 | 15 seconds + jitter | Add `random(0, 2)` seconds. |
| 4 | 60 seconds + jitter | Add `random(0, 2)` seconds. |
| After attempt 4 | — | Emit `ESCALATION(UNRESOLVABLE_CONFLICT)`. Do not retry further. |

Jitter rule: add `random(0, 2)` seconds to each non-zero wait. Never add jitter to attempt 1.

Log every attempt with: `attempt_number`, `wait_seconds`, `jitter_applied`, `provider`, `http_status`, `timestamp`.

---

## Model Fallback Chain

When `EXTERNAL_API_FAILURE` persists after backoff exhaustion on the primary provider:

**Anthropic:**
```
claude-opus-4-6 → claude-sonnet-4-6 → claude-haiku-4-5-20251001
```

**OpenAI:**
```
gpt-4o → gpt-4o-mini
```

**Local fallback (any cloud failure):**
```
any cloud provider → ollama (if available locally)
```

**Terminal condition:**
```
all providers failed → ESCALATION(UNRESOLVABLE_CONFLICT) + set session status="circuit_breaker"
```

Log every fallback step with all four fields:

```json
{
  "event": "model_fallback",
  "reason": "<failure description>",
  "provider_from": "<e.g. anthropic/claude-opus-4-6>",
  "provider_to": "<e.g. anthropic/claude-sonnet-4-6>",
  "timestamp": "<ISO 8601>"
}
```

---

## Circuit Breaker

**Trigger condition:** 3 consecutive node failures within the same session, regardless of fault type.

**Actions (execute in order):**

1. Stop all in-progress nodes immediately. Do not wait for pending responses.
2. Emit `ESCALATION(UNRESOLVABLE_CONFLICT)` to the PMIABroker.
3. Set session `status="circuit_breaker"` in session state.
4. Write a checkpoint containing the current session state, all completed node outputs, and the failure log.
5. Close the session cleanly via PHASE 8 abbreviated path (skip remaining phase steps, write final audit record).

**Reset condition:** The circuit breaker is NOT auto-reset within a session. A new session must be started. The checkpoint written in step 4 is available for the new session to resume from.

**Broker interaction:**

```json
{
  "msg_type": "ESCALATION",
  "reason": "UNRESOLVABLE_CONFLICT",
  "trigger": "circuit_breaker",
  "consecutive_failures": 3,
  "session_id": "<uuid>",
  "timestamp_ms": "<epoch ms>",
  "hmac": "<hmac-sha256>"
}
```

---

## Checkpoint Discipline

Before ANY irreversible action (git commit, file delete, API call with side effects), the executing agent MUST:

1. Emit `CHECKPOINT_REQ` to AuditAgent via PMIABroker.
2. Wait for AuditAgent acknowledgment. Timeout: 30 seconds.
3. Proceed only after receiving acknowledgment OR after the 30s timeout expires.
   - On timeout: log the timeout, proceed, and flag the action as `unacknowledged` in the audit trail.

**Crash recovery — orphaned actions:**

If the session crashes mid-irreversible-action:
- AuditAgent detects missing acknowledgment on session resume.
- AuditAgent marks the affected node as `ORPHANED`.
- AuditAgent triggers fault recovery: classify as `AGENT_TIMEOUT` and apply the corresponding recovery strategy.
- OrchestratorAgent is notified of the orphaned node before resuming any other work.

---

## SECURITY_VETO Response Protocol

When SecurityAgent issues `GATE_VERDICT(REJECTED)`:

1. OrchestratorAgent receives the verdict via PMIABroker (HMAC-SHA256 verified).
2. Do NOT retry the rejected operation under any circumstances.
3. Do NOT attempt to work around the veto by reformulating the request.
4. Log the full veto context (operation attempted, rationale, gate, timestamp) to `engram/security/<session_id>/`.
5. Surface the rejection reason to the user verbatim — do not paraphrase or soften.
6. The blocked node is permanently marked `PERMANENTLY_REJECTED` in session state.
7. The session may continue executing other non-blocked nodes. Only the specific blocked node is stopped.

**Veto log entry format:**

```json
{
  "event": "SECURITY_VETO",
  "gate": "<gate_id>",
  "rejected_operation": "<description>",
  "rationale": "<verbatim from SecurityAgent>",
  "node_id": "<node_id>",
  "session_id": "<uuid>",
  "timestamp": "<ISO 8601>",
  "status": "PERMANENTLY_REJECTED"
}
```

---

## WORKTREE_CONFLICT Resolution

**Detection:** Before each expert node writes a file, check the `_claimed_files` registry in session state. If the target path is already claimed by another node, a `WORKTREE_CONFLICT` is raised.

**Resolution options (apply in priority order):**

1. **Option A — Semantic re-assignment:** Determine which node logically owns the file based on its task scope. Re-assign the file exclusively to that node. The other node omits the file from its output. Use this when ownership is unambiguous.

2. **Option B — Serialization:** Pause node B. Let node A complete its write. Node B then reads node A's output and continues. Use this when both nodes need the file but in sequence.

3. **Option C — Merge node:** Allow both nodes to produce their outputs independently (to temporary paths). Create a dedicated merge node that receives both outputs and produces the final merged file. Use this when both nodes have equal and non-sequential claims.

4. **Last resort — Scope split:** Divide the conflicting file's content into separate files, each scoped to one node. Update all references accordingly.

Log a `CROSS_ALERT(severity=MEDIUM)` for every `WORKTREE_CONFLICT`, regardless of which resolution option is used.

---

## Fault Audit Trail

Every fault event MUST be logged to `engram/audit/<session_id>/faults.md` immediately upon detection.

**Required fields per entry:**

```markdown
### <ISO 8601 timestamp>

- **fault_type**: <one of the 7 types above>
- **agent_id**: <agent that failed or raised the fault>
- **node_id**: <worktree node identifier>
- **attempt_number**: <1-based count within this fault event>
- **recovery_action_taken**: <description of what was done>
- **result**: <one of: recovered | escalated | circuit_breaker>
```

**Retention:** Fault audit entries are immutable after write. Do not edit or delete existing entries. Append only.

**Flush condition:** Write entries immediately — do not batch. If the session crashes before a fault entry is written, AuditAgent reconstructs the entry on resume from available broker logs.

<!-- v5.1 — restored from v4 fault-recovery + circuit-breaker patterns -->
