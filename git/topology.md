# git/topology.md — Branch Topology

Read by: `sdk/core/init.py`, `agents/domain_orchestrator.md`, `sys/_index.md`

---

## Branch Types

All branches in this repository belong to one of two types. This classification
governs who may write to them, what they contain, and how they interact with
the agent pipeline.

### Directive Branches

Branches that define **how the system thinks and operates**. They carry
framework configuration, agent contracts, architectural decisions, and
meta-level context. They are never merged into artifact branches.

| Branch | Purpose |
|---|---|
| `architect` | Primary framework development branch. All changes to `sdk/`, `agents/`, `contracts/`, `sys/`, `git/` originate here. |
| `sec_ops` | Security operations branch. Dedicated to SecurityAgent contracts, gate policies, and audit rules. Isolated from product branches. |
| `piv-directive` | Orphan branch. SDK-managed only. Stores engram atoms written by AuditAgent. Never user-edited, never merged. |

**Invariants for directive branches:**
- Never merged into `main`, `staging`, or any `feature/*` branch
- Not subject to product CI pipelines (Gate 1 / Gate 2b / Gate 3 do not apply)
- Agents load their configs from directive branches at session start via `sdk/core/loader.py`
- Human push allowed on `architect` and `sec_ops`; SDK-only on `piv-directive`

### Artifact Branches

Branches that carry **product deliverables** — code that will be tested,
reviewed, and shipped. All agent execution (PHASE 5) happens in these branches.

| Branch | Purpose |
|---|---|
| `main` | Stable product. Gate 3 + human-only merge. Protected: no automated push, no force push. |
| `staging` | Integration layer. Created by `piv-oac init` if missing. Gate 2b required to merge from `feature/*`. |
| `feature/<task-id>/` | Task integration branch. Created by DomainOrchestrator at PHASE 5. |
| `feature/<task-id>/expert-N` | Specialist Agent worktree subbranch. |
| `fix/<issue-id>/` | Hotfix branches. Same expert model, shorter lifecycle. |

**Invariants for artifact branches:**
- All changes flow bottom-up: `expert-N` → `feature/` → `staging` → `main`
- No artifact branch reads from or merges directive branches
- Gate verdicts are required at each merge boundary (see `git/protection.md`)

---

## Branch Map

```
user-repo/
│
├── [directive branches — framework configuration, never merged into product]
│   ├── architect         ← framework development (sdk/, agents/, contracts/, sys/)
│   ├── sec_ops           ← security contracts + gate policies
│   └── piv-directive     ← orphan — SDK-managed engram atoms only
│
└── [artifact branches — product deliverables, full gate pipeline]
    ├── main              ← stable product
    │                       Gate 3 + human-only merge
    │                       Protected: no automated push, no force push
    │
    ├── staging           ← integration layer
    │                       Created by `piv-oac init` if missing
    │                       Gate 2b required to merge from feature/*
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

| Branch | Type | Created by | Deleted by | Trigger |
|---|---|---|---|---|
| `main` | Artifact | Repo init | Never | — |
| `staging` | Artifact | `piv-oac init` | Never | First `piv-oac init` run |
| `architect` | Directive | Human (manual) | Never | Framework repo setup |
| `sec_ops` | Directive | Human (manual) | Never | When security scope is separated |
| `piv-directive` | Directive | `piv-oac init` | Never | First `piv-oac init` run |
| `feature/<task-id>/` | Artifact | DomainOrchestrator | DomainOrchestrator | After Gate 2 APPROVED |
| `feature/<task-id>/expert-N` | Artifact | DomainOrchestrator | After Gate 1 APPROVED | Expert worktree creation |
| `fix/<issue-id>/` | Artifact | MasterOrchestrator | After Gate 2b | Hotfix classification |

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
