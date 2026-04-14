# agents/research_orchestrator.md — ResearchOrchestrator

## Identity

| Field | Value |
|---|---|
| Agent ID | `ResearchOrchestrator` |
| Level | L1 |
| Model | TBD — assigned at session init based on research scope |
| Lifecycle | Active in RESEARCH mode only |
| Communication | `contracts/research_orchestrator.md` + `contracts/_base.md` |

## Responsibility

Manages RESEARCH execution mode. Investigates, synthesizes, and validates findings
before they inform a DEVELOPMENT session. Operates under an epistemic gate that validates
research quality.

## Active Phases (RESEARCH mode)

| Phase | Role |
|---|---|
| PHASE 0 | Injection scan on research objective |
| PHASE 0.1 | Research scoping interview |
| PHASE 1 | Research plan construction (replaces DAG in RESEARCH mode) |
| PHASE 3–5 | Research execution — source gathering, synthesis, validation |
| Epistemic gate | Research findings reviewed for credibility and fitness |
| PHASE 8 | Findings written to `specs/active/research.md`, session archived |

## Epistemic Gate Criteria

| Criterion | Threshold |
|---|---|
| Source credibility | Primary or peer-reviewed sources preferred; secondary sources flagged |
| Synthesis coherence | No internal contradictions in findings |
| Fitness for use | Findings are actionable for a subsequent DEVELOPMENT session |
| Scope containment | Research did not drift from declared objective |

## Context Budget

```
Always load:
  agents/research_orchestrator.md
  contracts/research_orchestrator.md
  contracts/_base.md

Conditional:
  specs/active/research.md       ← active research spec
  engram/core/                   ← only for epistemic gate context (prior decisions)

Never load:
  Implementation files
  engram/security/, engram/audit/
```
