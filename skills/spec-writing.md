# skills/spec-writing.md — Spec Writing

## When to Load

When SpecWriter is writing PHASE 0.2 output or when reviewing spec quality.

## Output Files (specs/active/)

```
specs/active/
├── functional.md    ← ALWAYS written (Level 1 and 2)
├── architecture.md  ← Level 2 complex only
└── quality.md       ← ALWAYS written
```

## functional.md Required Fields

```yaml
objective: one-sentence goal
scope:
  - concrete deliverable 1
  - concrete deliverable 2
acceptance_criteria:
  - criterion that can be tested mechanically
```

Optional: `constraints`, `out_of_scope`

## architecture.md (Level 2 complex)

Contains structural decisions: patterns chosen, APIs designed, data model,
third-party integrations. Written in plain English sections.
No implementation details — architecture, not code.

## quality.md

```yaml
coverage_threshold: 80   # percent minimum
acceptance_checks:
  - All assigned tests pass
  - ruff check passes (zero errors)
  - No NotImplementedError remaining
```

## Spec Confirmation Protocol

1. SpecWriter writes files to `specs/active/`
2. Orchestrator presents spec summary to user
3. User confirms (or requests amendments)
4. **DAG is NOT built until user confirms**
5. Once confirmed: spec files are immutable for this session

## Spec Quality Checklist

- [ ] Objective is specific and measurable
- [ ] Scope items are achievable in one session
- [ ] Acceptance criteria are testable without human judgment
- [ ] No contradictions between functional.md and architecture.md
- [ ] Out-of-scope items explicitly listed (prevents scope creep)
