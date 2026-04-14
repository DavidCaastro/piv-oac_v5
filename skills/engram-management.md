# skills/engram-management.md — Engram Management

## When to Load

When AuditAgent is writing to engram or when troubleshooting access errors.

## Write Protocol (AuditAgent only)

```python
# Atomic write: temp file → rename (no partial writes)
import os

tmp = atom_path.with_suffix(".tmp")
tmp.write_text(new_content, encoding="utf-8")
os.replace(tmp, atom_path)  # atomic on POSIX and Windows
```

## Append Format

Every append begins with a metadata header:

```markdown
---
session_id: <uuid>
timestamp_iso: 2026-04-14T10:23:01.342Z
agent_id: AuditAgent
version: 1
---

<new content>
```

## EngramReader Usage (all other agents)

```python
from sdk.engram import EngramReader

reader = EngramReader(engram_root=Path("engram"), role="orchestrator")

# Check before loading (conditional lazy load)
if reader.exists("core/decisions.md"):
    content = reader.read("core/decisions.md")
```

`reader.read()` raises `EngramAccessError` if role is not authorized.

## Access Denial Handling

```
EngramAccessError raised:
  → Log: level=WARN, action=engram_access_denied
  → Do NOT escalate (access boundaries are expected constraints)
  → Continue without the atom (use only what is authorized)
```

## Pruning (AuditAgent, PHASE 8)

Check retention policy in `engram/VERSIONING.md`.
Remove expired atoms. Log each removal.
Never prune during PHASE 5 — active session data must be preserved.

## What Engram Is NOT

- A code mirror (never stores product source code)
- A backup system (pruned content is gone permanently)
- A shared scratchpad (append-only, AuditAgent-only writes)
