# skills/session-continuity.md — Session Continuity

## When to Load

When resuming an interrupted session, handling context expiry mid-session, writing
session closure artifacts at PHASE 8, or recovering from a partial DAG execution.

---

## Dual-Artifact System

Every session produces exactly two persistence artifacts. They serve different purposes
and have different mutability rules.

**Artifact A — `.piv/<session_id>/state.json`** (machine-readable state snapshot)

- Mutable throughout the session lifetime.
- Updated after every phase transition, gate verdict, and checkpoint trigger.
- Read by PHASE 0 Recovery Protocol to restore execution state.
- Moved to `.piv/completed/` or `.piv/failed/` at PHASE 8 close.

**Artifact B — `engram/audit/<session_id>/record.json`** (immutable audit record)

- Write-once. Written exactly once at PHASE 8 pre-close step.
- Contains the final snapshot of all gate verdicts, expert results, and token totals.
- Must NOT be modified after write. Any read of this file by a recovery protocol
  indicates the session already closed successfully.
- If `record.json` exists and `state.json` is absent → session is complete. Do not resume.

**Supplementary paths (read-only during recovery):**

```
.piv/<session_id>/checkpoints.jsonl  ← append-only event log during session
engram/audit/<session_id>/spec.md    ← TechSpecSheet (written at PHASE 8)
logs/index.jsonl                     ← session index entry (written at PHASE 8)
logs/sessions/<session_id>.jsonl     ← raw event stream
```

---

## Session State Schema

Full JSON schema for `.piv/<session_id>/state.json`. All fields are required unless
marked optional.

```json
{
  "session_id": "<uuid-v4>",
  "objective": "<verbatim objective string>",
  "provider": "anthropic",
  "status": "active",
  "phase_current": 0,
  "consecutive_rejections": 0,
  "fragmentation_depth": 0,
  "created_at": "<ISO-8601 UTC>",
  "updated_at": "<ISO-8601 UTC>",
  "dag_nodes": [
    {
      "node_id": "<uuid>",
      "phase": 5,
      "role": "ExpertAgent",
      "status": "pending | running | completed | failed | skipped",
      "engram_key": "<path or null>",
      "started_at": "<ISO-8601 or null>",
      "completed_at": "<ISO-8601 or null>",
      "circuit_breaker_trips": 0
    }
  ],
  "expert_results": [
    {
      "node_id": "<uuid>",
      "role": "ExpertAgent",
      "output_summary": "<≤200 token summary>",
      "engram_ref": "<engram/... path>",
      "verdict": "accepted | rejected | escalated"
    }
  ],
  "gate_verdicts": [
    {
      "gate_id": "GATE_0 | GATE_1 | GATE_2A | GATE_2B | GATE_3",
      "verdict": "pass | fail | conditional",
      "issued_at": "<ISO-8601 UTC>",
      "issuing_agent": "SecurityAgent | CoherenceAgent | AuditAgent",
      "conditions": []
    }
  ],
  "tokens_consumed": {
    "total": 0,
    "by_agent": {
      "OrchestratorAgent": 0,
      "SecurityAgent": 0,
      "ExpertAgent": 0,
      "CoherenceAgent": 0,
      "AuditAgent": 0
    }
  },
  "spec_rejection_log": [],
  "worktrees": []
}
```

**Field definitions:**

| Field | Description |
|---|---|
| `status` | `active` \| `completed` \| `circuit_breaker` \| `spec_rejected` |
| `phase_current` | Integer 0–8, current execution phase |
| `consecutive_rejections` | Incremented on each spec rejection; triggers circuit breaker at 3 |
| `fragmentation_depth` | Number of nested sub-agent fragmentations active |
| `circuit_breaker_trips` | Per-node; when ≥ 3 → escalate instead of retry |

---

## Session Summary Template

Used when emitting a CHECKPOINT_REQ message. Must not exceed 200 lines.

```
SESSION CONTINUITY SUMMARY
==========================
session_id : <uuid>
objective  : <verbatim, truncated to 120 chars if needed>
phase      : PHASE_<N> — <phase name>
status     : <active | circuit_breaker | spec_rejected>
as_of      : <ISO-8601 UTC>

COMPLETED NODES
---------------
[x] <node_id> — <role> — <one-line output summary>
[x] <node_id> — <role> — <one-line output summary>

PENDING NODES
-------------
[ ] <node_id> — <role> — <status: pending | running | failed>
[ ] <node_id> — <role> — <status>

GATE VERDICTS
-------------
| Gate    | Verdict     | Issued by        | Issued at        |
|---------|-------------|------------------|------------------|
| GATE_0  | pass        | SecurityAgent    | 2026-04-15T10:00Z|
| GATE_1  | pass        | CoherenceAgent   | 2026-04-15T10:05Z|
| GATE_2A | conditional | AuditAgent       | 2026-04-15T10:22Z|
| GATE_2B | pending     | —                | —                |
| GATE_3  | pending     | —                | —                |

TOKEN BUDGET STATUS
-------------------
Total consumed : <N> / 200,000 (<pct>%)
OrchestratorAgent : <N> / 40,000 (<pct>%)
SecurityAgent     : <N> / 30,000 (<pct>%)
ExpertAgent       : <N> / 60,000 (<pct>%)
CoherenceAgent    : <N> / 20,000 (<pct>%)
AuditAgent        : <N> / 15,000 (<pct>%)

BLOCKERS / WARNINGS
-------------------
- <blocker description if any, else "None">

NEXT ACTION
-----------
<single sentence: what the next execution step is>
```

---

## Checkpoint Triggers (automatic)

The following events MUST emit a CHECKPOINT_REQ to the broker automatically.
No agent may skip these triggers.

| Trigger Event | Emitting Agent | Condition |
|---|---|---|
| PHASE_1 DAG confirmed | OrchestratorAgent | DAG structure finalized, all nodes assigned |
| PHASE_5 batch completion | OrchestratorAgent | Each parallel batch of expert nodes completes |
| GATE_2B verdict | AuditAgent | Immediately after GATE_2B is issued (pass or fail) |
| PHASE_8 pre-close | AuditAgent | Before writing `record.json` |
| Token budget at 60% | Any agent | When `tokens_consumed / max_budget >= 0.60` |

**Manual trigger:** Any agent may emit CHECKPOINT_REQ when it detects a structural
anomaly (orphan node, missing engram, gate verdict older than 24h).

After emitting CHECKPOINT_REQ, the emitting agent writes the Session Summary
(see template above) to `.piv/<session_id>/checkpoints.jsonl` as an appended entry.

---

## PHASE 0 Recovery Protocol

Executed when a session is detected in `.piv/<session_id>/state.json` with
`status == "active"` but no active process holds a lock on it.

**Steps — execute in order. Do not skip any step.**

1. **JSON-first read.** Read `.piv/<session_id>/state.json`. If file is absent or
   unparseable → treat session as failed, move to `.piv/failed/`, start clean.

2. **Zero-trust validation.** Verify every `node_id` in `dag_nodes[]` is still
   structurally valid: role exists in `agents/`, contract exists in `contracts/`.
   Any node whose role has no matching contract → mark node `failed`, log reason.

3. **Orphan detection.** For each node with `status == "completed"`:
   - Check that `engram_key` resolves to an existing file.
   - If `engram_key` is null or file is absent → node is an orphan.
   - Orphaned nodes MUST be re-queued as `status = "pending"` and re-run.
   - Do not trust a `completed` status without a valid engram entry.

4. **Gate re-validation.** For each entry in `gate_verdicts[]`:
   - If `issued_at` is older than 24 hours → verdict is stale.
   - Stale verdicts MUST be cleared and the corresponding gate re-run.
   - A stale GATE_1 verdict means PHASE_1 must re-execute before PHASE_5 resumes.

5. **Resume from lowest incomplete phase.** Identify the lowest `phase_current`
   value across all nodes with `status != "completed"`. Resume execution from
   that phase. Do not jump to a later phase even if earlier phases appear complete,
   unless steps 1–4 have confirmed those completions with valid engram entries.

---

## PHASE 5 Expert Reactivation

When an ExpertAgent node has `status == "failed"` or its engram is incomplete,
execute this protocol before re-running the node.

1. **Read engram for partial output.** Load `engram_key` if it exists. Extract
   any partial structured output. This partial output is injected as prior context
   when retrying — do not discard it.

2. **Verify worktree still exists.** Check that the worktree path recorded in
   `worktrees[]` is present on disk. If absent → recreate the worktree using
   the same branch name and base commit recorded in state. If the branch no
   longer exists → re-create from `main` and emit a warning to the broker.

3. **Verify branch tracks remote.** Run a remote status check. If the branch has
   diverged from its remote tracking branch → re-sync (reset to remote HEAD)
   before injecting context. Do not retry on a diverged branch.

4. **Re-inject context from checkpoint.** Load the most recent CHECKPOINT_REQ
   entry from `checkpoints.jsonl` that predates this node's failure. Use the
   Session Summary from that checkpoint as the injected prior context for the
   retry. Compress to ≤500 tokens if needed (see context-management skill).

5. **Retry with same config unless circuit_breaker_trips ≥ 3.**
   - `circuit_breaker_trips < 3` → retry with identical node config.
   - `circuit_breaker_trips >= 3` → do NOT retry. Emit
     `ESCALATION(EXPERT_NODE_EXHAUSTED, node_id=<id>)` to OrchestratorAgent.
     OrchestratorAgent decides: reassign to a different expert role, split the
     node, or halt the session.

---

## Session Closure Protocol

PHASE 8 mandatory steps. AuditAgent owns this sequence. Steps must execute in order.
No step may be skipped. If any step fails, emit `ESCALATION(CLOSURE_FAILURE)`.

1. **Write `record.json`.**
   Write `engram/audit/<session_id>/record.json` with the final state snapshot.
   This file is write-once. Verify it does not already exist before writing.

2. **Append `gates/verdicts.md`.**
   Append the gate verdicts table (from Session Summary) to `gates/verdicts.md`.
   Create the file if absent. Format: one markdown table row per gate per session.

3. **Write index entry.**
   Call `write_index_entry()` to append one line to `logs/index.jsonl`.
   Entry must include: `session_id`, `objective` (truncated), `status`,
   `phase_current`, `created_at`, `updated_at`, `total_tokens_consumed`.

4. **Prune worktrees.**
   Call `worktree_prune()` for every entry in `worktrees[]`.
   Log each pruned worktree path to the session's event stream.

5. **Close broker.**
   Call `broker.close()`. This flushes all pending PMIA messages (GATE_VERDICT,
   ESCALATION, CROSS_ALERT, CHECKPOINT_REQ) and marks the channel as closed.
   No PMIA messages may be sent after this step.

6. **Close telemetry.**
   Call `telemetry.close()`. This finalizes token consumption totals and
   writes the telemetry record to `logs/sessions/<session_id>.jsonl`.

7. **Move state file.**
   Move `.piv/<session_id>/state.json` to `.piv/completed/<session_id>.json`
   (or `.piv/failed/` if `status == "circuit_breaker"`).

---

## Saturation Thresholds

Applies to the session-level total budget (200K tokens) and per-agent budgets.
Thresholds are evaluated after every agent response.

| Budget % | Action |
|---|---|
| 60% | Emit `CHECKPOINT_REQ`. Apply 6-step compression (see context-management skill). |
| 75% | Emit warning to telemetry. Log entry in `checkpoints.jsonl`. No pause. |
| 80% | `VETO_SATURACIÓN` candidate. OrchestratorAgent evaluates fragmentation. |
| 90% | Emit `CROSS_ALERT(severity=HIGH)` to broker. All non-critical work pauses. |
| 100% | Emit `ESCALATION(CONTEXT_SATURATION)`. Session halts. State saved to `.piv/`. |

Per-agent caps are defined in the context-management skill. A per-agent threshold
breach triggers the same sequence scoped to that agent, not the full session.

---

## Restrictions

Session-continuity does NOT do the following. Any deviation is a protocol violation.

- Does not read another session's `.piv/<other_id>/state.json`. Each session's
  state is isolated. Cross-session reads require explicit AuditAgent authorization.
- Does not modify `engram/audit/<session_id>/record.json` after it has been written.
  The record is immutable. If a post-close correction is needed, create a new
  session with a corrective objective.
- Does not skip PHASE 8 closure steps. Partial closure (e.g., writing record.json
  but not calling `broker.close()`) leaves the session in an undefined state
  that the Recovery Protocol cannot safely handle.
- Does not resume a session that has `record.json` present. Presence of record.json
  means the session completed. Attempting to resume it would corrupt the audit trail.
- Does not promote a stale gate verdict. Gate verdicts older than 24 hours must be
  re-run, not trusted.

<!-- v5.1 — expanded from v4 audit -->
