# skills/parallel-safety.md — Parallel Safety

## When to Load

When DomainOrchestrator launches multiple SpecialistAgents or when debugging isolation violations.

## Expert Isolation Boundary

Each SpecialistAgent operates in complete isolation until Gate 1:

```
Authorized reads (expert-N):
  worktrees/<task-id>/expert-N/**   ← own worktree only
  specs/active/<task>.md            ← own task spec only
  skills/<assigned>.md              ← declared skills, SHA-256 verified
  contracts/_base.md
  agents/specialist_agent.md

Prohibited reads:
  worktrees/<task-id>/expert-M/**  where M ≠ N
  engram/** (any)
  sys/**
  specs/active/<other-task>.md
```

## File Overlap Prevention

1. DomainOrchestrator declares `files_in_scope` per expert before Gate 2
2. Gate 2 review checks for overlap (no two experts write the same file)
3. If overlap detected: Gate 2 REJECTED, plan revised
4. ExecutionAuditor monitors during PHASE 5 for live violations

## CROSS_ALERT Conditions

ExecutionAuditor raises CROSS_ALERT to SecurityAgent when:
- A SpecialistAgent attempts to read outside its declared worktree
- File path in a commit touches a file declared in another expert's scope
- Checkpoint interval exceeds 3× the configured threshold

## No Shared State

SpecialistAgents do NOT share:
- Environment variables beyond what's declared in their spec
- Database connections (each test uses isolated fixtures)
- In-memory objects
- Git staging area (each works in own worktree)

## Gate 1 Synchronization Point

Gate 1 is the FIRST point where expert work is visible to others.
Before Gate 1: zero cross-expert visibility, by design.
