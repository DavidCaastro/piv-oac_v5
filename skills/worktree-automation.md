# skills/worktree-automation.md — Worktree Automation

## When to Load

When DomainOrchestrator creates, lists, or removes git worktrees.

## Lifecycle

```
Gate 2 APPROVED
    → DomainOrchestrator creates worktrees/<task-id>/expert-<N>
    → SpecialistAgent works in isolation
    → Gate 1 APPROVED (expert subbranch merged to task branch)
    → Worktree removed: git worktree remove worktrees/<task-id>/expert-<N>
    → Pruned: git worktree prune
```

## SDK Bootstrap Commands

```bash
bash sys/bootstrap.sh wt:add <task-id> <expert-N>     # create worktree
bash sys/bootstrap.sh wt:list                          # list all active worktrees
bash sys/bootstrap.sh wt:remove <task-id> <expert-N>  # remove specific worktree
bash sys/bootstrap.sh wt:prune                         # remove all stale references
```

## Naming Convention

```
worktrees/<task-id>/expert-<N>/
```

Examples:
- `worktrees/auth-001/expert-1/`
- `worktrees/payments-003/expert-2/`

## Isolation Invariants

- Worktrees are NEVER created before Gate 2 APPROVED
- Each expert's worktree is on its own branch (no shared working tree)
- SpecialistAgent reads only `worktrees/<task-id>/expert-N/**` (own path)
- DomainOrchestrator verifies no file overlap between experts before Gate 2

## Worktree State

```bash
git worktree list          # shows all registered worktrees
git worktree prune         # removes references to deleted worktrees
git worktree remove <path> # removes worktree (files + git reference)
```

`worktrees/` is gitignored — contents are ephemeral, not versioned.
