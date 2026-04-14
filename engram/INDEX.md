# engram/INDEX.md — Engram Memory Layer Index

**Sole writer:** AuditAgent
**Read access:** Role-scoped via `sdk/engram/reader.py`
**Versioning:** See `engram/VERSIONING.md`

---

## What Engram Is

Engram is the persistent, session-spanning memory layer of PIV/OAC.
It stores structured knowledge that agents accumulate across sessions —
architectural decisions, security events, evaluation scores, and more.

Engram is **not** a codebase mirror. It holds insights that cannot be derived
from reading the current code state.

---

## Lazy Load Invariant

Engram atoms are **never pre-loaded**.
Agents declare which atom they need and why.
`sdk/engram/reader.py` mediates every read.
Loading is conditional: only if a prior session produced relevant data.

---

## Directory Structure

```
engram/
├── INDEX.md            ← This file (navigation + policy)
├── VERSIONING.md       ← Atom versioning format and retention policy
│
├── core/               ← Cross-cutting decisions (all orchestrating agents)
│   └── decisions.md    ← Architectural decisions with rationale
│
├── domains/            ← Per-project domain knowledge
│   └── <project>/      ← One directory per user project
│       └── context.md  ← Domain-specific context (DomainOrchestrator)
│
├── security/           ← Security events and threat patterns
│   └── alerts.md       ← CROSS_ALERT history (SecurityAgent only)
│
├── audit/              ← Session records and TechSpecSheets
│   └── <session_id>/   ← One directory per completed session
│       ├── record.json ← Session state snapshot
│       └── spec.md     ← TechSpecSheet
│
├── metrics/            ← Aggregated quality metrics across sessions
│   └── scores.md       ← EvaluationAgent score history
│
├── skills/             ← Skill usage and effectiveness tracking
│   └── usage.md        ← Which skills were loaded, by which agents
│
├── gates/              ← Gate verdict history and circuit breaker events
│   └── verdicts.md     ← Gate outcomes with rationale
│
├── sessions/           ← Active session metadata (mirrors .piv/active/)
│   └── index.md        ← Session index for cross-session context
│
└── specs/              ← Confirmed spec history (post-PHASE 0.2)
    └── archive/        ← Archived specs/active/ contents per session
```

---

## Access Control Summary

| Subdirectory | Readers | Writer |
|---|---|---|
| `core/` | orchestrator, audit_agent, coherence_agent, domain_orchestrator, standards_agent, documentation_agent, research_orchestrator | AuditAgent |
| `domains/` | orchestrator, audit_agent, domain_orchestrator, documentation_agent, research_orchestrator | AuditAgent |
| `security/` | security_agent, audit_agent | AuditAgent |
| `audit/` | audit_agent, compliance_agent | AuditAgent |
| `metrics/` | audit_agent, evaluation_agent | AuditAgent |
| `skills/` | (reserved — not currently read by agents directly) | AuditAgent |
| `gates/` | (reserved — not currently read by agents directly) | AuditAgent |
| `sessions/` | (reserved — not currently read by agents directly) | AuditAgent |
| `specs/` | (reserved — not currently read by agents directly) | AuditAgent |

SpecialistAgents have **zero** engram access (isolation boundary enforced by `sdk/engram/reader.py`).

---

## Write Protocol (AuditAgent only)

1. Read existing atom (if present)
2. Append new content with session_id + timestamp header
3. Write atomically (temp file + rename — no partial writes)
4. Record write event in `logs/sessions/<session_id>.jsonl`

No agent other than AuditAgent may write to `engram/`.
All writes are append-only — no existing atom content is overwritten.
