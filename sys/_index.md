# sys/_index.md — Navigation Contract

> This file is the single routing authority for all agents after pre-flight verification.
> Read this after `sys/_verify.md` passes. Do not read other module files until this
> file tells you to.

---

## Routing Rule

After all BLOCKER checks in `sys/_verify.md` pass, every agent is routed to `sdk/`:

```
sdk/core/loader.py  instantiates the agent using:
  agents/<role>.md          ← role config, model assignment, phases
  contracts/<role>.md       ← role-specific PMIA contract
  contracts/_base.md        ← base protocol, gate invariants (always loaded)
```

No agent is instantiated without `contracts/_base.md`. It is mandatory for all roles.

---

## Load Table by Role

Agents load only what their role requires. Loading beyond this list is a context violation.

| Role | Always load | Load if condition | Never load |
|---|---|---|---|
| Master Orchestrator (L0) | `agents/orchestrator.md` `contracts/orchestrator.md` `contracts/_base.md` `git/topology.md` | `engram/core/` — only if prior session exists for this domain | Product workspace files, `engram/security/` |
| SecurityAgent (L1) | `agents/security_agent.md` `contracts/security_agent.md` `contracts/_base.md` | `engram/security/` — only if prior security events exist for this domain | Product workspace files |
| AuditAgent (L1) | `agents/audit_agent.md` `contracts/audit_agent.md` `contracts/_base.md` | `engram/audit/` `engram/precedents/` — only at phase exit or checkpoint write | Product workspace files |
| CoherenceAgent (L1) | `agents/coherence_agent.md` `contracts/coherence_agent.md` `contracts/_base.md` | `engram/coherence/` — only when a conflict is detected | Product workspace files |
| ComplianceAgent (L1) | `agents/compliance_agent.md` `contracts/compliance_agent.md` `contracts/_base.md` | `engram/compliance/` — FULL or MINIMAL scope trigger only | Product workspace files |
| EvaluationAgent (L1) | `agents/evaluation_agent.md` `contracts/evaluation_agent.md` `contracts/_base.md` `metrics/schema.md` | — | Product workspace files, `engram/` |
| StandardsAgent (L1) | `agents/standards_agent.md` `contracts/standards_agent.md` `contracts/_base.md` | — | Product workspace files, `engram/` |
| DocumentationAgent (L1) | `agents/documentation_agent.md` `contracts/_base.md` | Active spec files from `specs/active/` | Product workspace files, `engram/` |
| ResearchOrchestrator (L1) | `agents/research_orchestrator.md` `contracts/_base.md` | `engram/core/` — epistemic gate context only | Product workspace files |
| LogisticsAgent (L1) | `agents/logistics_agent.md` `contracts/logistics_agent.md` `contracts/_base.md` | — | `engram/`, product workspace files |
| ExecutionAuditor (L1) | `agents/execution_auditor.md` `contracts/execution_auditor.md` `contracts/_base.md` | — | `engram/`, product workspace files |
| Domain Orchestrator (L1.5) | `agents/domain_orchestrator.md` `contracts/domain_orchestrator.md` `contracts/_base.md` `git/topology.md` | `engram/core/` `engram/domains/<project>/` — only if prior session for this domain | `engram/security/`, product workspace files |
| Specialist Agent (L2) | `agents/specialist_agent.md` `contracts/specialist_agent.md` `contracts/_base.md` `specs/active/<task>.md` + assigned skills only | Product workspace — own task branch only | `engram/`, `sys/`, other task files |

---

## Load Table by Task

| Task | Load sequence |
|---|---|
| Session bootstrap | Root entrypoint → `sys/_verify.md` → `sys/_index.md` → `sdk/` |
| Gate evaluation | `contracts/_base.md` → agent-specific contract |
| Worktree operation | `sys/worktrees.md` → `sys/bootstrap.sh piv wt:*` |
| Skill loading | `skills/manifest.json` (SHA-256 verified) → `skills/<name>.md` |
| Engram write | `engram/INDEX.md` (AuditAgent only, at phase exit) |
| Engram read | `engram/INDEX.md` → agent declares atom + reason → `sdk/engram/reader.py` loads |
| Git operation | `git/topology.md` or `git/protection.md` → `sys/git.md` for connectivity rules |
| Compliance check | `contracts/compliance_agent.md` → `engram/compliance/` if triggered |
| Spec write (PHASE 0.2) | `sdk/core/spec_writer.py` → `specs/active/functional.md` + `specs/active/architecture.md` |

---

## Context Budget Rules

| Task | Read | Do NOT read |
|---|---|---|
| Implement a class | Its spec + its stub only | Other class stubs |
| Fix a bug | The buggy file + its spec | Unrelated modules |
| Add a config key | `config/settings.yaml` + relevant spec | Full codebase |
| Write tests | The spec's Testing section + the stub | Implementation details |
| Cross-module integration | Both specs + both stubs | Full directory tree |
| Gate evaluation | `contracts/_base.md` + agent contract | Everything else |

Rule: if a question can be answered from a spec or contract, do not open the `.py` file.

---

## Lazy Loading Invariant

No module is loaded speculatively. Every load must be:
1. **Declared** — the agent states which file it needs and why.
2. **Authorized** — the role's entry in the Load Table above permits it.
3. **Scoped** — the atom or file is released from context when the need is satisfied.

Loading more than declared is a context violation. `ExecutionAuditor` monitors for violations.
