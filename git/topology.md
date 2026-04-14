# git/topology.md — Branch Topology

Read by: `sdk/core/init.py`, `agents/domain_orchestrator.md`, `sys/_index.md`

---

## Branch Map

```
user-repo/
│
├── main              ← stable product
│                       Gate 3 + human-only merge
│                       Protected: no automated push, no force push
│
├── staging           ← integration layer
│                       Created by `piv-oac init` if missing
│                       Gate 2b required to merge from feature/*
│
├── piv-directive     ← orphan branch — framework configs
│                       SDK-managed only (never user-edited, never merged)
│                       Updated only on `pip install piv-oac` (version bump)
│
└── [session branches — created during PHASE 5, deleted after merge]
    │
    ├── feature/<task-id>/
    │   ├── feature/<task-id>/expert-1   ← Specialist Agent 1 worktree
    │   ├── feature/<task-id>/expert-2   ← Specialist Agent 2 worktree
    │   └── feature/<task-id>/expert-N   ← Specialist Agent N worktree
    │
    └── fix/<issue-id>/                  ← hotfix branches (same expert model)
```

---

## Branch Lifecycle

| Branch | Created by | Deleted by | Trigger |
|---|---|---|---|
| `main` | Repo init | Never | — |
| `staging` | `piv-oac init` | Never | First `piv-oac init` run |
| `piv-directive` | `piv-oac init` | Never | First `piv-oac init` run |
| `feature/<task-id>/` | DomainOrchestrator | DomainOrchestrator | After Gate 2 APPROVED |
| `feature/<task-id>/expert-N` | DomainOrchestrator | After Gate 1 APPROVED | Expert worktree creation |
| `fix/<issue-id>/` | MasterOrchestrator | After Gate 2b | Hotfix classification |

**feature/ branches and worktrees are NOT created at init.**
They are created by Domain Orchestrators during PHASE 5 as the DAG requires them.

---

## Branch Naming Convention

| Pattern | Usage |
|---|---|
| `feature/<task-id>/expert-<N>` | Specialist Agent subbranch (e.g. `feature/jwt-001/expert-1`) |
| `feature/<task-id>/` | Task integration branch (merge target for expert subbranches) |
| `fix/<issue-id>/` | Hotfix branch (same pattern, shorter lifecycle) |

`<task-id>` format: `<domain>-<sequential-number>` (e.g. `auth-001`, `payments-003`).
`<N>` is sequential: expert-1, expert-2, … (assigned by DomainOrchestrator).

---

## Two-Level Merge Strategy

```
expert-N subbranch
    ↓  Gate 1 (CoherenceAgent) — per expert
feature/<task-id>/ (task branch)
    ↓  Gate 2b (EvaluationAgent + SecurityAgent + StandardsAgent)
staging
    ↓  Gate 3 (ComplianceAgent + human approval)
main
```

No subbranch merges directly to staging.
No task branch merges to main without passing through staging.

---

## piv-directive Invariants

- Users never push to, merge from, or manually edit `piv-directive`
- SDK updates `piv-directive` only when a new version of `piv-oac` is installed
- AuditAgent writes engram atoms to `piv-directive` (append-only, no rebase)
- No CI pipeline merges `piv-directive` into any product branch
- Readable by agents via `sdk/core/loader.py` (checked out into `.piv/cache/` for reading)
