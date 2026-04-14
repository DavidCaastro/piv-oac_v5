# skills/gate-protocol.md — Gate Protocol

## When to Load

When an agent is evaluating or responding to a gate decision.

## Gate Overview

| Gate | Evaluator | Trigger | Verdict authority |
|---|---|---|---|
| Gate 0 | SecurityAgent only | Level 1 task (fast-track) | SecurityAgent |
| Gate 1 | CoherenceAgent | expert subbranch → task branch | CoherenceAgent |
| Gate 2 | Security + Audit + Coherence | Plan review before PHASE 5 | All three must APPROVE |
| Gate 2b | EvaluationAgent + SecurityAgent + StandardsAgent | task branch → staging (CI) | All must APPROVE |
| Gate 3 | ComplianceAgent + human | staging → main | ComplianceAgent prepares; human merges |

## GATE_VERDICT Message Format (PMIA v5.0)

```json
{
  "msg_type": "GATE_VERDICT",
  "gate": "GATE_1",
  "verdict": "APPROVED",
  "agent_id": "CoherenceAgent",
  "session_id": "<uuid>",
  "timestamp_ms": 1744790781342,
  "rationale": "No conflicts detected. Expert diffs are semantically compatible.",
  "hmac": "<hmac-sha256>"
}
```

## Gate Invariants (from contracts/_base.md)

- SecurityAgent unconditional veto: any gate, any phase
- No code reaches staging without Gate 2b APPROVED
- No code reaches main without Gate 3 + human approval
- Gate 2 requires ALL three agents APPROVED (not majority)
- GATE_VERDICT messages are logged to `logs/gates/<session_id>.jsonl`

## Circuit Breaker

```
3 consecutive GATE_VERDICT: REJECTED (any gate, same session)
→ GateEvaluator returns GateVerdict.ESCALATED
→ Session moved to .piv/failed/<session_id>.json
→ AuditAgent writes post-mortem to engram/audit/<session_id>/
```

## Agent Response on REJECTED Verdict

```
SpecialistAgent:
  1. Read rationale from gate verdict
  2. Address specific checks_failed items
  3. Re-commit and re-submit for gate review
  4. Do NOT re-submit without addressing ALL failed checks
```
