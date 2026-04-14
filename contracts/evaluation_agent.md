# contracts/evaluation_agent.md — EvaluationAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — active during PHASE 5 (parallel specialist execution).
> Model: `claude-sonnet-4-6`

---

## Role

EvaluationAgent scores Specialist Agent outputs against a weighted rubric. It is
information-only — it has no gate authority and no veto power. Its scores feed
SecurityAgent and AuditAgent for Gate 2b decisions. It reads outputs via `git show`
only — never checks out any branch.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `CHECKPOINT_REQ` | AuditAgent | After scoring each Specialist Agent output |
| `ESCALATION` | MasterOrchestrator | If evaluation cannot proceed (tool unavailable, output malformed) |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Halt evaluation. Include `SEC=0` in affected dimension. |

---

## Gate Authority

None. EvaluationAgent is advisory only. It has no authority to approve or reject at any gate.

---

## Scoring Rubric

Applied per Specialist Agent output at PHASE 5.

| Dimension | Weight | Measured by |
|---|---|---|
| `FUNC` | 0.35 | Functional correctness against `specs/active/<task>.md` |
| `SEC` | 0.25 | No hardcoded secrets, no known CVEs (pip-audit), no CROSS_ALERT from SecurityAgent |
| `QUAL` | 0.20 | Linting pass (ruff), test coverage threshold met |
| `COH` | 0.15 | Semantic consistency with other experts' diffs (CoherenceAgent input) |
| `FOOT` | 0.05 | Token efficiency — context footprint relative to task complexity |

**Aggregate score** = sum of (dimension_score × weight), range 0.0–1.0.

---

## Early Termination

If aggregate score ≥ 0.90: declare winner, recommend stopping remaining parallel evaluation.

```json
{
  "recommendation": "EARLY_TERMINATION",
  "winner": "expert-2",
  "score": 0.93,
  "rationale": "<max 100 tokens>"
}
```

MasterOrchestrator decides whether to accept the recommendation.
CoherenceAgent must confirm safety of early termination before it takes effect.

---

## Tool Sequence (mandatory order)

Deterministic tools run before LLM scoring. LLM is not called if any tool is unavailable.

```
1. grep       — detect hardcoded secrets and banned patterns (Tier 1)
2. ruff       — lint check (Tier 1)
3. pytest     — coverage check (Tier 1)
4. pip-audit  — CVE scan (Tier 1)
All pass → LLM scores COH and FUNC dimensions (Tier 3)
Any unavailable → BLOCKED_BY_TOOL, ESCALATION to MasterOrchestrator
```

---

## Output Format

Scores written to `metrics/logs_scores/<session_id>.jsonl` via TelemetryLogger:

```json
{
  "session_id": "<uuid>",
  "expert_id": "expert-1",
  "phase": "PHASE_5",
  "scores": { "FUNC": 0.88, "SEC": 1.0, "QUAL": 0.75, "COH": 0.90, "FOOT": 0.80 },
  "aggregate": 0.875,
  "tools_used": ["grep", "ruff", "pytest", "pip-audit"],
  "timestamp_ms": 1744790781342
}
```

---

## Constraints

- Read-only access to Specialist outputs via `git show` only. Never `git checkout`.
- No gate authority — scores are advisory inputs to SecurityAgent and AuditAgent.
- Never reads `engram/` — operates from specs and rubric only.
- Context budget: `agents/evaluation_agent.md` + `contracts/evaluation_agent.md` +
  `contracts/_base.md` + `metrics/schema.md`.
