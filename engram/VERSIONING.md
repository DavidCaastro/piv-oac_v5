# engram/VERSIONING.md — Atom Versioning and Retention Policy

---

## Atom Header Format

Every engram atom entry (append) must begin with a versioned header:

```markdown
---
session_id: <uuid>
timestamp_iso: 2026-04-14T10:23:01.342Z
agent_id: AuditAgent
version: 1
---

<atom content here>
```

The `version` field increments with each PIV/OAC framework version that changes
the atom schema. Content from older schema versions is retained but marked
`[legacy — schema v<N>]` if incompatible.

---

## Atom Versioning Rules

| Rule | Detail |
|---|---|
| Append-only | No atom content is ever overwritten or deleted by agents |
| Header required | Every append must include the metadata header above |
| Atomic writes | Write to `.tmp` first, then `mv`/rename — no partial writes |
| Session-scoped | Each append is linked to exactly one session_id |
| Schema v1 | Current format — increment when structure changes |

---

## Retention Policy

| Atom type | Retention | Rationale |
|---|---|---|
| `core/decisions.md` | Permanent | Architectural decisions are not time-bounded |
| `domains/<project>/` | Per-project lifecycle | Removed when project is archived |
| `security/alerts.md` | 90 days (rolling) | Security events degrade in relevance |
| `audit/<session_id>/` | 30 completed sessions | Older sessions pruned by AuditAgent |
| `metrics/scores.md` | 60 days | Quality trends require recent data |
| `skills/usage.md` | 30 days | Recency matters for skill effectiveness |
| `gates/verdicts.md` | 60 days | Circuit breaker analysis window |
| `sessions/index.md` | Active sessions only | Cleared on session.close() |
| `specs/archive/` | 5 sessions per project | Reference for regression detection |

---

## Pruning

AuditAgent is responsible for enforcing retention.
Pruning occurs at **PHASE 8** (session closure) — never during active execution.

Pruning is logged to `logs/sessions/<session_id>.jsonl` with:
```json
{
  "action": "engram_prune",
  "atoms_removed": ["audit/session-old-id/"],
  "reason": "retention_limit_exceeded"
}
```

No pruned content is recoverable. Engram is not a backup system.

## skills-manifest
02fcbc836b79a2bbf2b2ea77802ab3fae462b0e2a6a7f288033999f11d0fbd78  skills/manifest.json
