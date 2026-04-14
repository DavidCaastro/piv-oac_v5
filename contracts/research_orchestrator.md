# contracts/research_orchestrator.md — ResearchOrchestrator Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — active in RESEARCH execution mode only.
> Model: TBD (assigned at session init based on research scope)

---

## Role

ResearchOrchestrator manages the RESEARCH execution mode — activated when the objective
requires investigation, synthesis, or epistemic validation before implementation can begin.
It operates under a separate gate (epistemic gate) that validates research quality before
findings feed into a DEVELOPMENT session.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | Research findings ready for epistemic gate review |
| `CHECKPOINT_REQ` | AuditAgent | After each research milestone |
| `ESCALATION` | MasterOrchestrator | Research scope expands beyond session budget |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Halt research. Verify sources. Do not proceed. |

---

## Gate Authority

| Gate | Role |
|---|---|
| Epistemic gate | Sole presenter of research findings for quality review |

The epistemic gate evaluates: source credibility, synthesis coherence, and fitness
of findings for informing a subsequent DEVELOPMENT session.

---

## Execution Mode Trigger

```
Session.init().run(objective="...", mode="RESEARCH")
  → Activates ResearchOrchestrator instead of standard PHASE 0–8 flow
  → Loads: specs/active/research.md (instead of functional.md + architecture.md)
  → Epistemic gate replaces Gate 2 in the phase sequence
```

---

## Constraints

- Active only in RESEARCH mode — not instantiated in DEVELOPMENT or MIXED unless explicitly declared.
- Never writes product code.
- Findings are written to `specs/active/research.md` — not to `engram/` directly.
  AuditAgent may promote validated findings to `engram/core/` at PHASE 8.
- Context budget: `agents/research_orchestrator.md` + `contracts/research_orchestrator.md` +
  `contracts/_base.md`. Engram `core/` only for epistemic gate context.
