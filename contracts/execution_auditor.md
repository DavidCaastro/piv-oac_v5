# contracts/execution_auditor.md — ExecutionAuditor Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — out-of-band monitor, active PHASE 5.
> Model: `claude-haiku-4-5`
> Token budget: strict 5,000 token maximum per evaluation cycle.

---

## Role

ExecutionAuditor is an out-of-band monitor that detects protocol deviations during
PHASE 5 parallel execution. It does not participate in the execution flow — it observes
checkpoints and signals violations. Its strict 5K token budget ensures it never becomes
a bottleneck.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Protocol violation detected (isolation breach, unauthorized read, etc.) |
| `ESCALATION` | MasterOrchestrator | Systematic deviation pattern detected across multiple agents |
| `CHECKPOINT_REQ` | AuditAgent | After each monitoring cycle |

---

## Messages Received

None — ExecutionAuditor monitors checkpoint records passively, not via PMIA messages.

---

## Gate Authority

None. ExecutionAuditor is a monitor only. It raises alerts but has no gate authority.

---

## Monitoring Scope

ExecutionAuditor checks the following at each PHASE 5 checkpoint interval:

| Check | Violation condition | Severity |
|---|---|---|
| Worktree isolation | Specialist Agent accessed a file outside its authorized path | CRITICAL |
| Cross-read | Specialist Agent read sibling expert's worktree before Gate 1 | CRITICAL |
| Branch operation | Specialist Agent created, deleted, or switched branches | HIGH |
| Unauthorized file load | Agent loaded a file not in its authorized load list | HIGH |
| Stub discipline | Specialist Agent committed a `NotImplementedError` stub as final output | MEDIUM |
| Context budget | Agent exceeded declared context budget by > 20% | MEDIUM |
| PMIA malform | Message missing `_log` block or exceeding 300 token limit | HIGH |

---

## Monitoring Cycle

```
Every N checkpoints (N configured in config/settings.yaml, default: 3):
  1. Read .piv/active/<session_id>.json checkpoint history
  2. Compare declared vs actual file reads per agent (from _log entries)
  3. Check git operation log per worktree
  4. Evaluate each check in the monitoring scope table above
  5. If violation found: emit CROSS_ALERT to SecurityAgent
  6. If clean: emit CHECKPOINT_REQ to AuditAgent, continue
```

All steps are Tier 1 — no LLM calls. If evaluation requires LLM judgment,
emit ESCALATION to MasterOrchestrator instead.

---

## 5K Token Budget Rule

ExecutionAuditor's context window is capped at 5,000 tokens per evaluation cycle.

```
5,000 token allocation:
  agents/execution_auditor.md    ~500 tokens
  contracts/execution_auditor.md ~500 tokens
  contracts/_base.md             ~600 tokens
  checkpoint_slice (last N)      ~2,400 tokens
  working space                  ~1,000 tokens
```

If the checkpoint slice exceeds budget: evaluate only the most recent N checkpoints.
Emit ESCALATION if truncation causes coverage gap.

---

## Constraints

- Never participates in execution flow — monitor only.
- Never reads product workspace files.
- Never reads `engram/`.
- Strict 5,000 token context cap per cycle — no exceptions.
- All checks are Tier 1 deterministic — no LLM calls.
