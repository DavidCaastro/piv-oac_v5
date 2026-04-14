# sys/worktrees.md — Worktree Lifecycle Directives

> Rules for git worktree management in PIV/OAC v5.0.
> Worktrees are the isolation mechanism for parallel Specialist Agent execution.
> Domain Orchestrators create them. Gate 1 triggers their removal.

---

## Purpose

Each Specialist Agent (L2) works in an isolated git worktree mapped to a feature branch.
This guarantees that parallel agents cannot read each other's in-progress work before Gate 1.

```
staging
└── feature/<task-id>/                    ← Domain Orchestrator scope
    ├── feature/<task-id>/expert-1        ← Specialist Agent 1 worktree
    ├── feature/<task-id>/expert-2        ← Specialist Agent 2 worktree
    └── feature/<task-id>/expert-N        ← Specialist Agent N worktree
```

---

## Naming Convention

| Component | Pattern | Example |
|---|---|---|
| Worktree path | `worktrees/<task-id>/<expert-N>` | `worktrees/auth-jwt/expert-1` |
| Branch name | `feature/<task-id>/expert-<N>` | `feature/auth-jwt/expert-1` |
| Task ID | kebab-case, derived from objective slug | `auth-jwt`, `payment-stripe` |
| Expert N | sequential integer starting at 1 | `expert-1`, `expert-2` |

---

## Lifecycle

### Phase: Creation (PHASE 5, after Gate 2 approval)

Gate 2 must be approved before any worktree is created. This is a hard invariant.

```bash
# Domain Orchestrator creates each expert worktree via bootstrap.sh
bash sys/bootstrap.sh wt:add <task-id> <expert-N>

# Equivalent git command:
git worktree add worktrees/<task-id>/<expert-N> -b feature/<task-id>/expert-<N>
```

### Phase: Active (PHASE 5 — Specialist Agent running)

- Each Specialist Agent reads only its own worktree + `specs/active/<task>.md` + assigned skills.
- No cross-worktree reads before Gate 1. This is enforced by `ExecutionAuditor`.
- `CoherenceAgent` reads diffs only (`git diff`) — never checks out any worktree.
- `EvaluationAgent` reads outputs via `git show` only — never runs `git checkout`.

### Phase: Removal (after Gate 1 merge)

After CoherenceAgent approves a subbranch merge into `feature/<task-id>/`:

```bash
bash sys/bootstrap.sh wt:remove worktrees/<task-id>/<expert-N>

# Equivalent:
git worktree remove worktrees/<task-id>/<expert-N>
git branch -d feature/<task-id>/expert-<N>
```

### Phase: Prune (maintenance)

Stale worktree references (CHECK 8 in `_verify.md`) are cleaned with:

```bash
bash sys/bootstrap.sh wt:prune
# Equivalent: git worktree prune
```

---

## Invariants

| Rule | Detail |
|---|---|
| Gate 2 before creation | No worktree is created without Gate 2 approval. Hard block. |
| Isolation during PHASE 5 | Specialists read only their own worktree + specs + assigned skills |
| No cross-read | Specialists cannot access sibling worktrees before Gate 1 |
| Cleanup at Gate 1 | Worktree and branch are deleted immediately after Gate 1 merge |
| Not versioned | `worktrees/` is gitignored — never committed, never shared |
| Path convention | Always `worktrees/<task-id>/<expert-N>` — no deviations |

---

## Resource Notes

- Each active worktree consumes ~disk space of the branch delta from `staging`.
- Active worktrees share the object store — no full repo duplication.
- Domain Orchestrator tracks active worktrees in `.piv/active/<session>.json`
  under `worktrees_active[]`.
- On session failure (circuit breaker): all worktrees for that session are listed
  in `.piv/failed/<session>.json` for manual cleanup review.
