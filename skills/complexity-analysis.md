# skills/complexity-analysis.md — Complexity Analysis

## When to Load

When refining the ComplexityClassifier heuristics or debugging Level assignment.

## Classification Flow (Tier 1, deterministic)

```
Objective received
    → ComplexityClassifier.classify(objective)
    → Level 1: fast-track (Gate 0, skip interview)
    → Level 2: PHASE 0.1 interview activates
```

## Level 1 Criteria (ALL must hold)

- ≤ 2 file references in objective
- No architectural keywords present
- Objective ≤ 80 characters OR micro-keyword present
- No ambiguity signals (no "or", "maybe", "could", "?")

## Level 2 Criteria (ANY suffices)

- Architectural keyword present (auth, database, integration, payment, etc.)
- > 2 file references
- Objective is ambiguous (multiple interpretations)
- Explicit question marks or "could"/"maybe"

## Architectural Keywords (partial list)

```
authentication, authorization, database, migration, integration,
payment, oauth, jwt, security, encryption, architecture, refactor,
multi, parallel, distributed, microservice, event, queue, webhook
```

## Micro Keywords (partial list)

```
typo, rename, comment, docstring, readme, format, indent, bump version
```

## Gate 0 Fast-Track (Level 1 only)

- 60-second budget max
- SecurityAgent only (no other agents)
- Injection scan → complexity confirm → execute
- No interview, no DAG, no DomainOrchestrator

## Adding Keywords

Keywords live in `sdk/utils/complexity.py` as frozen sets.
Changes require a spec update + StandardsAgent approval (skill knowledge change).
