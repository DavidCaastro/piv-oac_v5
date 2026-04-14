# PIV/OAC v5.0 — Foundational Seed Document

> This file is non-operational. It contains no shell commands, no scripts, no implementation
> detail. Its purpose is to describe the seed from which the entire framework grows —
> the "what" and "why" before the "how".
>
> Read by: humans onboarding to the framework, bootstrapping agents building from scratch,
> any agent that needs to understand why a structural decision was made.
>
> NOT read by: runtime agents executing tasks. They start from `sys/_index.md`.

---

## 1. Document Purpose

`_init_.md` answers three questions that every other document in this repository assumes
you already know:

1. **What is PIV/OAC?** — The problem it solves and the principles it operates under.
2. **How is the repository structured?** — What each layer and module owns, and what it does not.
3. **Why does it exist?** — The rationale behind decisions that would otherwise seem arbitrary.

This document is the entry point for understanding. It is not the entry point for execution.
If you are an agent ready to work, read `sys/_index.md` instead.

---

## 2. Framework Identity

**PIV/OAC** — Paradigm of Verifiable Intentionality / Atomic Context Orchestration

| Field | Value |
|---|---|
| Full name | Paradigm of Verifiable Intentionality / Atomic Context Orchestration |
| Version | 5.0 |
| Repository | `piv-oac_v5` |
| Published package | `piv-oac` on PyPI |
| Language policy | All repository content in English |
| Previous version | v4.0 (internal, production-validated) |

### What it is

PIV/OAC is an AI-guided software development framework that enforces **verifiable intent**
and **atomic context orchestration** as non-negotiable operating conditions.

It is not a code generation tool. It is not an automation layer. It is a **verified execution
environment** in which AI agents operate under deterministic governance rules — gates that
block, contracts that constrain, and audit trails that persist across sessions.

The two core ideas:

**Verifiable Intentionality**: no agent executes anything without a confirmed, human-approved
specification. The raw objective is never the source of truth. Specs are. The distance between
"what the user said" and "what the agent understood" must be zero before execution begins.

**Atomic Context Orchestration**: each agent loads only the minimum context required for its
specific role and task. No agent reads the entire codebase. No agent holds more context than
it needs. Context is a resource — rationed, not broadcast.

---

## 3. The Problem Space

Conventional AI-guided development fails in predictable ways. PIV/OAC exists because these
failures are structural, not accidental, and require structural solutions.

### What breaks without this framework

| Failure mode | Cause | Consequence |
|---|---|---|
| Hallucination | Agent acts on assumed intent, not verified intent | Code that satisfies the wrong objective |
| Context saturation | Agent reads more than it needs to | Degraded reasoning, irrelevant output, wasted tokens |
| Architectural drift | Each session starts without memory of prior decisions | Contradictory implementations across sessions |
| Security as afterthought | Security review happens after code is written | Vulnerabilities embedded before any gate can catch them |
| Parallel conflicts | Multiple agents write without awareness of each other | Merge conflicts, semantic contradictions, broken contracts |
| Unauditable decisions | No record of why a choice was made | Cannot reproduce, cannot roll back, cannot learn |

### Why determinism-first matters

Any operation that can be resolved by formula, heuristic, regex, or local computation
**must not** invoke a language model. LLM calls are reserved for genuine reasoning —
situations where ambiguity is real and rule-based resolution is insufficient.

This is not a cost-cutting measure. It is a correctness measure. Deterministic operations
are reproducible, auditable, and immune to hallucination. Every LLM call is a trust boundary
that must be justified.

The framework classifies every operation before executing it:
- **Tier 1** — always local, always deterministic: SHA-256 verification, injection scanning,
  complexity classification, gate logic, session state management, log writing.
- **Tier 2** — optional local inference: mechanical L2 tasks offloaded to a local model
  when hardware permits.
- **Tier 3** — cloud inference: genuine reasoning tasks that cannot be resolved locally.

---

## 4. Framework Differentiators

PIV/OAC is differentiated by invariants, not features. An invariant is a condition that
cannot be bypassed — not by an agent, not by a workflow, not by an admin.

### Capability comparison

| Capability | PIV/OAC | LangGraph | AutoGen | CrewAI |
|---|---|---|---|---|
| Multi-agent blocking security gates | ✅ | ❌ | ❌ | ❌ |
| Gate 3: human-only merge to main | ✅ | Partial | ❌ | ❌ |
| ComplianceAgent with legal/ethical gate | ✅ | ❌ | ❌ | ❌ |
| Intent verification before execution | ✅ | ❌ | ❌ | ❌ |
| Zero-trust session continuity with checkpoint | ✅ | Partial | ❌ | ❌ |
| RESEARCH mode with epistemic gate | ✅ | ❌ | ❌ | ❌ |
| Context saturation veto with escalation cascade | ✅ | ❌ | ❌ | ❌ |
| Skill integrity via SHA-256 manifest | ✅ | ❌ | ❌ | ❌ |
| Engram: cross-session persistent memory | ✅ | ❌ | Partial | ❌ |
| Tier 1/2/3 routing (determinism-first) | ✅ | ❌ | ❌ | ❌ |

### Non-negotiable invariants

These cannot be configured away, disabled, or overridden by any agent contract:

1. No worktree is created before Gate 2 approval.
2. `main` is unreachable by any automated process without explicit human confirmation (Gate 3).
3. SecurityAgent veto overrides all other approvals at any gate and at any phase.
4. Every LLM call is preceded by `Vault.scanForInjection()`.
5. AuditAgent is the only writer to `engram/`.
6. Skills are loaded only after SHA-256 manifest verification. Hash mismatch halts the session.
7. Credentials never appear in agent context, messages, or logs — only names, never values.

---

## 5. Layer Map

The repository is organized in three distinct layers. Each layer has a single responsibility,
a defined reading order, and a hard boundary on what it does not own.

```
┌─────────────────────────────────────────────────────────────────┐
│  ROOT LAYER                                                     │
│                                                                 │
│  Owns: framework identity, provider entrypoints, build context  │
│  Does NOT own: logic, commands, module content, credentials     │
│                                                                 │
│  Files: _init_.md  _context_.md  README.md  .gitignore         │
│         pyproject.toml  CLAUDE.md  anthropic.py  ollama.py      │
│         openai.py                                               │
└──────────────────────────────┬──────────────────────────────────┘
                               │ agent reads entrypoint → redirected to
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  sys/ — GATEKEEPER + ENVIRONMENT LAYER                          │
│                                                                 │
│  Owns: pre-flight verification, navigation contract             │
│  Does NOT own: domain logic, agent definitions, business rules  │
│                                                                 │
│  Step 1 — Pre-flight verification (_verify.md + bootstrap.sh):  │
│    venv · git connectivity · credentials · env vars             │
│    SHA-256 manifest · session state · stale worktrees           │
│                                                                 │
│  Step 2 — Route to sdk/ for agent instantiation (_index.md)     │
│                                                                 │
│  Files: _index.md · _verify.md · bootstrap.sh                  │
│         venv.md · worktrees.md · git.md                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ verification passes → routes to
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  sdk/ — FRAMEWORK ENGINE  (publishable Python package)          │
│                                                                 │
│  Owns: Python implementation, provider routing, session logic   │
│  Does NOT own: markdown content (reads it from sibling modules) │
│                                                                 │
│  Published as "piv-oac" on PyPI. Loads and operationalizes      │
│  agents/, contracts/, skills/, engram/ at runtime.              │
└──────────────────────────────┬──────────────────────────────────┘
                               │ loads markdown from
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE LAYER  (siblings at root — source of truth)             │
│                                                                 │
│  agents/      contracts/    skills/     engram/                 │
│  specs/       metrics/      git/        .github/                │
│  observability/  config/    tests/      logs/                   │
└─────────────────────────────────────────────────────────────────┘
```

### Reading order by role

| Role | Entry point | Then reads |
|---|---|---|
| Human onboarding | `_init_.md` (this file) | `_context_.md` → `sys/_index.md` |
| Bootstrapping agent | `_init_.md` | `_context_.md` → specs in build order |
| Runtime agent | `CLAUDE.md` or provider script | `sys/_index.md` → role-specific modules |
| Developer debugging | `_context_.md` | Relevant spec or module file |

---

## 6. Module Map

Every module lives at root level as a sibling directory. Modules do not load each other.
`sdk/core/loader.py` reads them. `sys/_index.md` tells agents which ones to load and when.

| Module | What it owns | Detail |
|---|---|---|
| `agents/` | Per-agent configuration: role, model, phases, context budget | One file per agent (13 agents) |
| `contracts/` | Inter-agent communication standard (PMIA v5.0) | `_base.md` + one file per agent |
| `skills/` | Lazy-loaded operational knowledge modules | 21 files + `manifest.json` (SHA-256) |
| `engram/` | Cross-session persistent memory, atomized by domain | AuditAgent sole writer |
| `specs/` | Specification templates and confirmed active specs | `_templates/` + `active/` (gitignored) |
| `metrics/` | Session evaluation schema and scoring records | `schema.md` + `logs_scores/` |
| `git/` | Branch topology, protection rules, commit policy | `topology.md`, `protection.md`, `policy.md` |
| `.github/` | GitHub Actions workflow files | `gate2b.yml`, `pre-merge.yml`, `staging-gate.yml` |
| `observability/` | Optional Docker stack: Grafana + Loki + Tempo + OTEL | Activated on demand, never during sessions |
| `config/` | Runtime YAML configuration | `settings.yaml`, `injection_patterns.yaml` |
| `logs/` | Session event logs, gate verdicts, evaluation scores | gitignored, local only |
| `tests/` | SDK unit and integration tests | SDK code only — product tests live in product repos |
| `sdk/` | Python engine: loader, session, DAG, vault, gates, providers | Publishable package |

For load order and agent-to-module routing, see `sys/_index.md`.

---

## 7. Core Principles

These principles are not guidelines — they are constraints. Every architectural decision
in this framework can be derived from them. When two approaches conflict, these principles
are the tiebreaker.

### 7.1 Determinism-First

Any operation resolvable by formula, heuristic, regex, or local computation must not invoke
a language model. LLM calls are a trust boundary reserved for genuine ambiguity.

Deterministic zone (no LLM, ever): SHA-256 verification, injection scanning, complexity
classification, DAG construction, gate logic evaluation, session state management,
token budget calculation, score aggregation, log writing.

### 7.2 Spec-First Execution

No implementation receives code without a confirmed, human-approved specification.
The raw objective is never the source of truth. The interview protocol (PHASE 0.1)
extracts what is unknown. Spec reformulation (PHASE 0.2) produces the source of truth.
The DAG is built only after the user confirms the specs.

Level 1 micro-tasks (≤2 files, unambiguous, low risk) skip the interview — the spec
is inferred directly. Everything else goes through the full protocol.

### 7.3 Zero-Trust Security

- Credentials never appear in agent context, PMIA messages, or log entries.
- `Vault.scanForInjection()` precedes every LLM call — no exceptions.
- SecurityAgent has unconditional veto authority at any phase and any gate.
- Skills are SHA-256 verified before loading. Hash mismatch stops the session immediately.
- `main` is unreachable by automated processes. Gate 3 requires explicit human confirmation.

### 7.4 Maximal Local Delegation

Every operation that the local machine can handle correctly must not leave the local machine.
This is not optional on resource-constrained machines — it is the design baseline.

Local delegation includes: all Tier 1 deterministic operations, pre-commit hooks,
SHA-256 manifest verification, session state I/O, log writing, and sys/_verify.md checks.
Tier 2 local inference is available when hardware permits. Tier 3 cloud is reserved for
L0/L1 reasoning tasks that cannot be delegated.

### 7.5 Strict Auditability

Every action, decision, and gate outcome is traceable and timestamped.

- AuditAgent is the sole writer to `engram/` and the sole issuer of session checkpoints.
- Every gate verdict is logged: timestamp (ms), agent, rationale, outcome.
- Every agent response carries a `_log` block consumed by `TelemetryLogger`.
- Session state is tracked in `.piv/active/`, `.piv/completed/`, `.piv/failed/`.
- Circuit breaker (3 consecutive rejections at the same gate) moves the session to
  `.piv/failed/` and writes a post-mortem to `engram/audit/`.

### 7.6 Structural Separation of Concerns

| Layer | Owns | Does NOT own |
|---|---|---|
| Root | Identity, entrypoints, build context | Logic, commands, module content |
| `sys/` | Environment setup, navigation contract, verification | Business logic, agent definitions |
| `sdk/` | Python implementation, provider routing | Markdown content (reads it from modules) |
| Module layer | Domain knowledge and execution rules | Cross-module routing (that belongs to `sys/`) |

No module imports another module. No layer owns the concerns of another layer.
If content requires reading a sibling file to make sense, it is in the wrong place.

---

## 8. Version History

### v4.0 → v5.0: What changed and why

**v4.0** was production-validated (OBJ-003 closed 2026-04-02, gate compliance 18/18).
Its architecture was sound. Its problems were structural, not conceptual:

| v4.0 limitation | v5.0 solution | Rationale |
|---|---|---|
| Monolithic `agent.md` — all agents in one file | Per-agent files in `agents/` | Context budget: agents load only their own config |
| Skills as the protocol layer (inter-agent-protocol as skill) | `contracts/_base.md` as mandatory base contract | Protocol must be invariant, not lazy-loaded |
| `agent-configs` orphan branch as governance layer | `sys/` as gatekeeper in `main` | Eliminates branch-switching overhead for governance reads |
| `scripts/validate_env.py` standalone script | `sys/_verify.md` + `sys/bootstrap.sh` | Unified verification contract, no detached scripts |
| Mixed Spanish/English across all files | English-only policy, enforced at commit level | Consistency, international readability, no ambiguity |
| No publishable package | `piv-oac` on PyPI | Mode 2 deployment: pip install into existing project |
| Static Vault document | MCP Vault + env vars at session init | Credentials never at rest in the repository |
| Eager engram loading by agent role | Lazy, conditional, declared atom loading | Context budget: only load what the current task needs |
| Observability as a skill module | `TelemetryLogger` class + optional Docker stack | Observability is infrastructure, not knowledge |
| Complexity forced through full interview | ComplexityClassifier gates the interview | Level 1 tasks should not pay the full interview cost |

### What did NOT change from v4.0

The gate system (0, 1, 2, 2b, 3), the agent hierarchy (L0/L1/L1.5/L2), the PMIA
inter-agent protocol, the Engram system design, the SecurityAgent unconditional veto,
the AuditAgent exclusive write authority, and the blameless culture model are all
carried forward from v4.0 without modification to their core logic.

v5.0 is a structural reorganization and a packaging of v4.0's proven concepts —
not a rethinking of them.
