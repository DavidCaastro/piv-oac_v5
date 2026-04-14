# skills/evaluation-rubric.md — Evaluation Rubric

## When to Load

When EvaluationAgent scores Specialist Agent output at Gate 2b.

## Dimensions and Weights

| Dimension | Weight | Description |
|---|---|---|
| FUNC (Functional) | 0.35 | Does it do what the spec says? |
| SEC (Security) | 0.25 | No vulnerabilities, no hardcoded secrets, passes pip-audit |
| QUAL (Quality) | 0.20 | ruff clean, type hints, no dead code |
| COH (Coherence) | 0.15 | Integrates cleanly with existing codebase |
| FOOT (Footprint) | 0.05 | Token budget reasonable, no over-engineering |

## Scoring Formula

```
weighted_score = FUNC*0.35 + SEC*0.25 + QUAL*0.20 + COH*0.15 + FOOT*0.05
```

Each dimension is scored 0.0 – 1.0. Weighted score range: 0.0 – 1.0.

## Evaluation Tool Sequence (mandatory order)

```
1. grep    ← hardcoded secret pattern scan (Tier 1)
2. ruff    ← lint + format check (Tier 1)
3. pytest  ← run assigned tests (Tier 1)
4. pip-audit ← dependency CVE scan (Tier 1)
5. LLM review ← FUNC + COH dimensions (Tier 3)
```

LLM review only runs if all Tier 1 tools pass. If any tool unavailable → BLOCKED_BY_TOOL.

## Early Termination

If weighted_score ≥ 0.90 after LLM review:
→ Emit recommendation: "early termination — score satisfactory"
→ Gate 2b evaluator may approve without further review

## Score Interpretation

| Score | Meaning |
|---|---|
| ≥ 0.90 | Excellent — early termination recommendation |
| 0.80 – 0.89 | Good — approve with minor notes |
| 0.70 – 0.79 | Acceptable — approve with required fixes |
| < 0.70 | Reject — fundamental issues, must revise |

EvaluationAgent is information-only. Final Gate 2b decision belongs to the gate.
