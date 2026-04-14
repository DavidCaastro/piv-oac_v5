# skills/research-methodology.md — Research Methodology

## When to Load

When ResearchOrchestrator is operating in RESEARCH mode.

## RESEARCH Mode Phases

| Phase | Action |
|---|---|
| PHASE 0 | Injection scan on research objective |
| PHASE 0.1 | Research scoping interview (always active in RESEARCH mode) |
| PHASE 1 | Research plan construction (replaces DAG) |
| PHASE 3–5 | Source gathering, synthesis, validation |
| Epistemic gate | Findings reviewed for credibility and fitness |
| PHASE 8 | Findings written to `specs/active/research.md`, session archived |

## Epistemic Gate Criteria

| Criterion | Threshold |
|---|---|
| Source credibility | Primary or peer-reviewed preferred; secondary sources flagged |
| Synthesis coherence | No internal contradictions in findings |
| Fitness for use | Findings are actionable for a DEVELOPMENT session |
| Scope containment | Research did not drift from declared objective |

## Source Quality Tiers

| Tier | Examples | Weight |
|---|---|---|
| Primary | RFC specs, official API docs, original papers | High |
| Secondary | Well-known engineering blogs, documented case studies | Medium |
| Tertiary | Stack Overflow, forum posts, undated articles | Low — flag explicitly |

## Output Format (specs/active/research.md)

```markdown
# Research: <objective>

## Summary
<2-3 paragraph synthesis>

## Key Findings
1. Finding with source citation
2. ...

## Recommendations for DEVELOPMENT Session
- Specific actionable items

## Sources
- [Source title](URL) — credibility: PRIMARY/SECONDARY/TERTIARY
```

## Transition to DEVELOPMENT

Research findings inform but do not replace the DEVELOPMENT interview.
A DEVELOPMENT session starts fresh with research.md loaded as context.
