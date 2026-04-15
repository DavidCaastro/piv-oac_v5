# skills/context-management.md — Context Management

## When to Load

When managing context budgets, lazy loading, or context saturation recovery.
Also load when any agent reaches a saturation threshold, when fragmenting a node,
or when evaluating whether to serialize a parallel DAG batch.

---

## Core Rule

Load the minimum context required to complete the current task.
Never pre-load. Declare what you need and why before loading.

---

## Context Budget Tiers

Per-agent hard caps and threshold actions. Budgets are enforced independently.
A per-agent breach does not automatically trigger a session-level breach, but
any agent at 80%+ must notify OrchestratorAgent immediately.

| Agent Type | Max Tokens | Warning at | VETO_SATURACIÓN at |
|---|---|---|---|
| OrchestratorAgent | 40,000 | 60% (24,000) | 80% (32,000) |
| SecurityAgent | 30,000 | 60% (18,000) | 80% (24,000) |
| ExpertAgent | 60,000 | 60% (36,000) | 80% (48,000) |
| CoherenceAgent | 20,000 | 60% (12,000) | 80% (16,000) |
| AuditAgent | 15,000 | 60% (9,000) | 80% (12,000) |
| StandardsAgent | 20,000 | 60% (12,000) | 80% (16,000) |

Session-level total budget: **200,000 tokens**. Session-level thresholds follow
the same 60%/80% pattern and are evaluated in parallel with per-agent thresholds.

---

## 60% Protocol — 6-Step Compression

When any agent reaches 60% of its individual budget, execute these steps in order
before continuing the task. Do not skip steps. Do not continue the task until
compression is confirmed complete.

1. **Emit CHECKPOINT_REQ.** The affected agent emits `CHECKPOINT_REQ` to the
   broker with its current token count, role, and node_id. This triggers a
   session state write (see session-continuity skill).

2. **Summarize completed context to ≤500 tokens.** Produce a structured summary
   of all completed sub-tasks and decisions made so far in the current node.
   This summary replaces the full prior transcript going forward. The summary
   must be deterministic: same inputs → same summary structure.

3. **Drop raw tool outputs.** Remove all raw tool call outputs from the active
   context. Retain only structured results: parsed JSON, extracted fields,
   explicit verdicts. If a raw output has not been parsed yet, parse it now,
   then drop the raw form.

4. **Prune duplicate messages.** Scan the transcript for duplicate or near-duplicate
   messages (same role, same content within 5% edit distance). Keep the most
   recent instance only. System-role messages are exempt from pruning.

5. **Compact engram references.** Replace any inline engram content with a pointer:
   `engram_ref: <path>`. Do not load the content again unless explicitly required
   by a later step. The pointer is sufficient for the agent to re-load on demand.

6. **Resume with compressed context.** Verify that post-compression token count
   is below 50% of budget. If not below 50% → do not resume; emit
   `ESCALATION(CONTEXT_SATURATION)` immediately and halt the node.

---

## VETO_SATURACIÓN Trigger

**Definition:** When an agent reaches 80% of its individual token budget, it emits
`VETO_SATURACIÓN(agent=<role>, node_id=<id>, tokens=<count>)` to the broker.
OrchestratorAgent receives this event and must evaluate the following decision tree
synchronously before allowing the agent to continue.

**Decision tree (evaluate in order):**

```
(a) Can the task be split into smaller sub-nodes?
    YES → Fragment: create a new DAG node for the remaining work.
          Inject only the structured output produced so far into the child node.
          Increment fragmentation_depth in session state.
          Resume the child node with a fresh context budget.

    NO  → continue to (b)

(b) Can the context be compressed further?
    (Apply 60% Protocol again — second pass)
    VERIFY: post-compression budget < 50%?
    YES → Resume the original agent at the reduced budget.

    NO  → continue to (c)

(c) Neither split nor compression resolved the problem.
    Emit ESCALATION(UNRESOLVABLE_CONFLICT, cause=CONTEXT_SATURATION).
    Trigger circuit breaker for this node (increment circuit_breaker_trips).
    Do not retry automatically. OrchestratorAgent decides next action.
```

OrchestratorAgent must respond to `VETO_SATURACIÓN` within the same execution turn.
Silence or delay is treated as option (c).

---

## Cascade Protocol (VETO_SATURACIÓN_CASCADA)

When 2 or more agents emit `VETO_SATURACIÓN` within the same DAG batch execution:

1. **Pause the entire batch.** No agent in the batch may continue processing.
   All in-flight tool calls complete but no new turns begin.

2. **OrchestratorAgent evaluates shared context.** Identify whether the agents
   in the batch share a common large context block (e.g., the same spec file,
   the same engram content, the same injected transcript). If a shared block
   accounts for >30% of each agent's consumed budget → it can be factored out.

3. **Shared context node (if factorable).** Create a shared context node:
   - Write the shared content to a new engram key.
   - Replace the inline content in each agent's context with an `engram_ref` pointer.
   - Resume the batch. Each agent reloads the shared content on demand, not upfront.

4. **Serialize the batch (if not factorable).** Remove parallelism for this DAG level.
   Execute the batch agents sequentially, one at a time. Each agent starts with
   a clean context budget. Pass only structured outputs between agents, not transcripts.

5. **Emit CROSS_ALERT.** Regardless of which path was taken (3 or 4), emit
   `CROSS_ALERT(severity=HIGH, cause=VETO_SATURACION_CASCADA, batch_size=<N>)`
   to the broker. This alert is logged in the session's event stream and
   included in the PHASE 8 audit record.

---

## Load Order

Context is loaded in this order, strictly. Do not load a later tier before
completing the current tier. Each tier must be verified before proceeding.

| Priority | Tier | Content | Rule |
|---|---|---|---|
| 1 | Contracts | `contracts/<role>.md` + `contracts/_base.md` | Always first. Required. |
| 2 | Skill | The declared skill file (this file, or session-continuity, etc.) | Load only declared skills. |
| 3 | Engram checkpoint | Most recent CHECKPOINT_REQ entry from `checkpoints.jsonl` | Load only if resuming a node. |
| 4 | Task context | `specs/active/<task>.md` — own task only | One file. Own task only. Never cross-load. |
| 5 | Tool results | Structured outputs from tool calls made in this turn | On-demand. Drop raw form immediately. |

Do not load tier N+1 if tier N has caused the budget to exceed 60%. Apply the
60% Protocol before continuing to the next tier.

---

## InheritanceGuard

Rules governing what context a child node inherits from its parent node.

**A child node inherits ONLY:**

- `session_id` and `objective` (always injected, never omitted).
- Parent node's structured output — the parsed, summarized result, not the raw transcript.
  Maximum size: 500 tokens. If the parent's output exceeds this, summarize before injecting.
- Gate verdicts up to and including the current phase. Format: compact table (≤100 tokens).

**A child node NEVER inherits:**

- Parent's full tool call history. Tool calls are local to the node that made them.
- Other sibling nodes' context, transcripts, or partial outputs. Siblings are isolated.
  If a child needs sibling output, it must read from the sibling's engram entry, not
  from an in-memory context pass-through.
- Any content that was pruned during the parent's 60% compression. Pruned content
  is considered non-essential and must not be re-injected downstream.

InheritanceGuard is enforced by OrchestratorAgent at node creation time. Violations
must be rejected before the child node's first turn begins.

---

## Saturation Recovery Sequence

Post-VETO_SATURACIÓN recovery steps, executed in order. This sequence applies
after OrchestratorAgent has determined that fragmentation was not possible (option c
in the VETO_SATURACIÓN decision tree was not reached, i.e., compression alone must resolve it).

```
Step 1 — Emit checkpoint.
    Agent emits CHECKPOINT_REQ. Session state is written to disk.
    This ensures recovery is possible if Step 2–4 fail.

Step 2 — Apply 60% Protocol (second pass).
    Execute all 6 steps of the compression protocol.
    Measure post-compression budget.

Step 3 — Verify recovery.
    Post-compression token count must be < 50% of agent's max budget.
    IF < 50% → proceed to Step 4.
    IF >= 50% → do NOT proceed. Emit ESCALATION(CONTEXT_SATURATION).
                OrchestratorAgent receives escalation and must act.

Step 4 — Resume.
    Agent resumes the task with the compressed context.
    Log the compression event to the session's event stream with:
    before_tokens, after_tokens, compression_ratio.
```

If ESCALATION(CONTEXT_SATURATION) is emitted at Step 3, the node is halted.
OrchestratorAgent may then apply fragmentation (option a of the decision tree)
or circuit-break the node.

---

## What NOT to Do

Violations of these rules are protocol errors. Agents must refuse instructions
that would cause any of the following.

- **Do not pass full transcripts between agents.** Only structured outputs and
  engram references cross agent boundaries. Raw message history stays local.
- **Do not load all engrams at once.** Engram entries are loaded on demand,
  one at a time, justified by the current task. Bulk loading is prohibited.
- **Do not ignore saturation warnings.** A 60% threshold event requires the
  6-step compression before the next agent turn. Skipping compression and
  continuing is a protocol violation.
- **Do not load files outside the declared load order.** The load order is
  enforced. Loading tier 4 (task context) before tier 2 (skill) is prohibited.
- **Do not load another agent's contract or spec.** Each agent loads only its
  own role files. Cross-role reads require explicit OrchestratorAgent instruction.
- **Do not load historical sessions** unless AuditAgent is performing authorized
  pattern analysis. Historical session data is never injected into active agent context.
- **Do not load product source code.** Agents read specs and structured outputs,
  not raw source files. Source code is the domain of ExpertAgent worktrees, not
  agent context.

<!-- v5.1 — expanded from v4 audit -->
