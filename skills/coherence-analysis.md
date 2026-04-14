# skills/coherence-analysis.md — Coherence Analysis

## When to Load

When CoherenceAgent evaluates a diff at Gate 1 (expert → task) or Gate 2b.

## Scope Rule

CoherenceAgent reads **diffs only** — never full source files.
This minimizes context consumption and maintains isolation integrity.

## Git Commands (allowed at Gate 1)

```bash
git diff <base>...<head>           # full diff for review
git diff <base>...<head> --stat    # file-level summary
git log <base>..<head> --oneline   # commit history
```

## Git Commands (prohibited)

```bash
git checkout <branch>   # never switch branches
git merge               # never merge
git rebase              # never rebase
```

## Conflict Classification

| Type | Action |
|---|---|
| Resolvable (non-overlapping files, style differences) | APPROVED with note |
| Resolvable (overlapping edits, compatible semantics) | APPROVED with merge guidance |
| Non-resolvable (semantic contradiction in shared logic) | REJECTED — Specialist Agent must resolve |
| Non-resolvable (security scope conflict) | REJECTED + CROSS_ALERT to SecurityAgent |

## Semantic Conflict Signals

- Two experts modify the same function with incompatible logic
- Import chains that would create circular dependencies
- Conflicting data model assumptions (field name, type, nullability)
- Incompatible API contracts (one expert changes a signature another depends on)

## CoherenceAgent Is NOT

- A code reviewer (that is StandardsAgent + EvaluationAgent)
- A merge tool (that is git)
- A security evaluator (that is SecurityAgent)

Focus: "Will these changes work together as a cohesive whole?"
