# skills/git-branch-automation.md — Git Branch Automation

## When to Load

When DomainOrchestrator creates branches/worktrees or when merging expert subbranches.

## Branch Creation (PHASE 5, after Gate 2 APPROVED)

```bash
# Create task integration branch (from staging)
git checkout staging
git checkout -b feature/<task-id>/

# Create expert subbranch (from task branch)
git checkout feature/<task-id>/
git checkout -b feature/<task-id>/expert-<N>

# Create worktree for expert (isolated filesystem)
git worktree add worktrees/<task-id>/expert-<N> feature/<task-id>/expert-<N>
```

## Branch Naming Convention

| Branch | Owner | Example |
|---|---|---|
| `feature/<task-id>/expert-<N>` | SpecialistAgent N | `feature/auth-001/expert-1` |
| `feature/<task-id>/` | DomainOrchestrator | `feature/auth-001/` |
| `fix/<issue-id>/` | MasterOrchestrator | `fix/bug-042/` |

## Gate 1 Merge (expert → task)

```bash
git checkout feature/<task-id>/
git merge --squash feature/<task-id>/expert-<N>
git commit -m "feat(<scope>): <description> [expert-<N>]"
git worktree remove worktrees/<task-id>/expert-<N>
```

## Safety Rules

| Allowed | Prohibited |
|---|---|
| Agents push to own subbranch | Agents push to staging or main |
| Squash merge expert → task | Force push any branch |
| DomainOrchestrator creates feature/ | Any agent merges to main |
| SDK creates piv-directive entries | Rebasing shared branches |

## Post-Gate Cleanup

```bash
# After Gate 2b (task → staging merged)
git branch -d feature/<task-id>/expert-<N>
git branch -d feature/<task-id>/
git worktree prune  # remove stale worktree references
```

Cleanup is performed by DomainOrchestrator, not by SpecialistAgents.
