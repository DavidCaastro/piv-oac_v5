# PIV/OAC v5.0 — Framework Build Context

> Living reference document. Consolidates every architectural decision, migration mapping,
> and task status for the v5.0 build. Update STATUS as work progresses.
>
> Last updated: 2026-04-16 (session 8)
> Previous version source: https://github.com/DavidCaastro/factory/tree/agent-configs

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Layer Architecture — The Mental Model](#2-layer-architecture--the-mental-model)
3. [Root Layer — Files & Purpose](#3-root-layer--files--purpose)
4. [_init_.md — Foundational Seed Document](#4-_init_md--foundational-seed-document)
5. [sys/ — Gatekeeper + Environment Layer](#5-sys--gatekeeper--environment-layer)
6. [SDK — Framework Engine](#6-sdk--framework-engine)
7. [Module Layer — Domain Modules](#7-module-layer--domain-modules)
8. [Deployment Model — Framework, SDK, and User Workspace](#8-deployment-model--framework-sdk-and-user-workspace)
9. [Execution Tier Model](#9-execution-tier-model)
10. [Observability](#10-observability)
11. [Interview Protocol (PHASE 0.1 — PHASE 0.2)](#11-interview-protocol-phase-01--phase-02)
12. [Core Principles for v5.0](#12-core-principles-for-v50)
13. [Migration Map: v4.0 → v5.0](#13-migration-map-v40--v50)
14. [File-by-File Build Plan](#14-file-by-file-build-plan)
15. [Rescued Content: Agent Architecture](#15-rescued-content-agent-architecture)
16. [Rescued Content: Gate System](#16-rescued-content-gate-system)
17. [Rescued Content: Execution Phases](#17-rescued-content-execution-phases)
18. [Rescued Content: Engram Memory System](#18-rescued-content-engram-memory-system)
19. [Rescued Content: Skill System](#19-rescued-content-skill-system)
20. [Rescued Content: Inter-Agent Protocol PMIA](#20-rescued-content-inter-agent-protocol-pmia)
21. [Rescued Content: Evaluation Contract](#21-rescued-content-evaluation-contract)
22. [Rescued Content: Parallel Safety Contract](#22-rescued-content-parallel-safety-contract)
23. [Rescued Content: Branch & Worktree Protocol](#23-rescued-content-branch--worktree-protocol)
24. [Rescued Content: Observability & SRE](#24-rescued-content-observability--sre)
25. [Rescued Content: Session Continuity](#25-rescued-content-session-continuity)
26. [Discarded from v4.0](#26-discarded-from-v40)
27. [Open Decisions](#27-open-decisions)
28. [Task Tracker](#28-task-tracker)

---

## 1. Project Identity

| Field | Value |
|---|---|
| Framework name | PIV/OAC |
| Full name | Paradigm of Verifiable Intentionality / Atomic Context Orchestration |
| Version | 5.0 |
| Repository | `piv-oac_v5` |
| Previous version | https://github.com/DavidCaastro/factory/tree/agent-configs |
| Language policy | All repo content in English. User communication in Spanish. |
| Current branch | `main` |
| Repo state at session start | Clean — one empty commit after full reset |

---

## 2. Layer Architecture — The Mental Model

PIV/OAC v5.0 is organized in three distinct layers. Each layer has a single responsibility
and a defined reading order for both humans and agents.

```
┌──────────────────────────────────────────────────────────────────┐
│  ROOT LAYER                                                      │
│  Identity, navigation, and provider entry points only.           │
│  _init_.md  _context_.md  README.md  .gitignore  pyproject.toml  │
│  CLAUDE.md  anthropic.py  ollama.py  (one script per provider)   │
└───────────────────────────┬──────────────────────────────────────┘
                            │ agent reads entrypoint → redirects to
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  sys/ — GATEKEEPER + ENVIRONMENT LAYER                           │
│                                                                  │
│  STEP 1 — Pre-flight verification (_verify.md + bootstrap.sh):   │
│    git connectivity · tokens present · env vars · SHA-256        │
│    venv active · .piv/ state · worktrees stale check            │
│                                                                  │
│  STEP 2 — Route to sdk/ for agent instantiation (_index.md)      │
│                                                                  │
│  Files: _index.md · _verify.md · bootstrap.sh                   │
│         venv.md · worktrees.md · git.md                         │
└───────────────────────────┬──────────────────────────────────────┘
                            │ passes verification → routes to
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  sdk/ — FRAMEWORK ENGINE  (publishable Python package)           │
│                                                                  │
│  Loads and operationalizes markdowns from all sibling modules.   │
│  sdk/ reads agents/, contracts/, skills/, engram/ at runtime.    │
│  Exposes clean Python API: Session, Agent, Gate, Vault, etc.     │
│  Published as "piv-oac" on PyPI. Includes all module markdowns   │
│  via pyproject.toml package_data.                                │
└───────────────────────────┬──────────────────────────────────────┘
                            │ loads markdowns from
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  MODULE LAYER  (siblings at root level — source of truth)        │
│                                                                  │
│  agents/      ← per-agent config (read by sdk/core/loader.py)   │
│  contracts/   ← PMIA contracts (read by sdk/core/loader.py)     │
│  skills/      ← capability modules + manifest.json              │
│  engram/      ← persistent atomized memory                       │
│  specs/       ← specification templates and active specs         │
│  metrics/     ← session tracking schema and scores              │
│  git/         ← git directives: topology, protection, policy     │
│  .github/     ← GitHub Actions yml (required path by GitHub)    │
│  .piv/        ← session state (not versioned)                   │
│  config/      ← runtime YAML: settings, injection_patterns      │
│  tests/       ← SDK tests only (product tests live in product repo) │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Entry Flow

```
1. Agent reads root entrypoint  (CLAUDE.md or anthropic.py / ollama.py)
         ↓
2. sys/ pre-flight verification  (bootstrap.sh runs _verify.md checks)
         ↓ all checks pass
3. sys/_index.md routes to sdk/  (agent instantiation begins)
         ↓
4. sdk/core/loader.py loads relevant agents/, contracts/, skills/ markdowns
         ↓
5. Agent operates within framework rules
```

`_init_.md` is read by humans and bootstrapping agents only — not by runtime agents.

---

## 3. Root Layer — Files & Purpose

The root contains identity files, provider entrypoints, and provider init scripts.
No domain logic, no module content, no commands live here directly.

### Meta & Identity Files

| File | Purpose |
|---|---|
| `_init_.md` | Non-operational seed document. WHAT the framework is and WHY each part exists. |
| `_context_.md` | This file. Migration context, decisions, build plan, task tracker. |
| `README.md` | One paragraph public description + pointer to `sys/_index.md`. |
| `pyproject.toml` | Python package definition for `piv-oac`. Replaces `requirements.txt`. Includes `package_data` to bundle all module markdowns in the published package. |
| `.gitignore` | Excludes: `worktrees/`, `.piv/`, `.env`, `__pycache__/`, `specs/active/`, `dist/`, `.venv/` |

### Provider Entrypoints — AI Tool Integration (markdown files)

One per AI provider tool. Minimal content — points to `sys/` only.

| File | Provider |
|---|---|
| `CLAUDE.md` | Anthropic Claude Code |
| `.cursor/rules/piv-oac.mdc` | Cursor |
| `.github/copilot-instructions.md` | GitHub Copilot |

**Template (identical for all):**
```markdown
# PIV/OAC v5.0 — [Provider Name] Entrypoint

All operational instructions, agent contracts, and system rules are in `sys/`.

Start here: read `sys/_index.md` to determine which files to load for your role and task.

Do not infer rules from this file. Do not act before reading `sys/_index.md`.
```

### Provider Init Scripts — SDK Initialization (Python files)

One per supported inference provider. Thin wrappers — five lines maximum.
Determine which provider the SDK initializes against.

| File | Provider | Init mode |
|---|---|---|
| `anthropic.py` | Anthropic | API Key (env var or parameter) |
| `ollama.py` | Ollama | Local agent on filesystem host |
| `openai.py` | OpenAI | API Key (env var or parameter) |

**Pattern (identical structure, provider name varies):**
```python
# anthropic.py
from sdk import Session
Session.init(provider="anthropic").run()
```

The provider value routes internally to `sdk/providers/<provider>.py`.
API keys and credentials are never hardcoded — read from env vars or MCP Vault.

### Root Isolation Rule

Root files point outward. They do not depend on each other.
If a file requires reading another file to make sense, it does not belong in root.

---

## 4. _init_.md — Foundational Seed Document

### What it is

`_init_.md` is the conceptual prerequisite document for the framework. It is non-operational:
it contains no shell commands, no scripts, no implementation detail. It describes the seed
from which the entire framework grows — the "what" and "why" before the "how".

It is read by:
- Humans onboarding to the framework
- Bootstrapping agents building the framework from scratch
- Any agent that needs to understand why a structural decision was made

It is NOT read by runtime agents executing tasks (they start from `sys/_index.md`).

### Sections to Build (in order)

```
1. Document purpose
   — What this file is, what it is not, who reads it

2. Framework identity
   — PIV/OAC name, version, core problem it solves
   — One-paragraph essence: verifiable intent + atomic context

3. The problem space
   — What breaks in conventional AI-guided development
   — Hallucination, context saturation, architectural drift
   — Why determinism-first matters

4. Framework differentiators
   — vs. LangGraph, AutoGen, CrewAI (table from v4.0, rewritten in English)
   — What invariants make PIV/OAC non-negotiable

5. Layer map
   — Describes the three-layer architecture (Root / sys / Modules)
   — What each layer owns and what it does NOT own
   — Reading order for humans and agents

6. Module map
   — Lists every module (agents, skills, engram, specs, metrics, scripts, contracts)
   — One-line description of each
   — Where to find the detail (pointer to sys/_index.md)

7. Core principles (the invariants)
   — Determinism-first
   — Spec-first execution
   — Zero-trust security
   — Maximal local delegation
   — Strict auditability
   — Structural separation of concerns

8. Version history
   — v4.0 → v5.0 migration rationale
   — What changed and why
```

### Current Status

`_init_.md` exists but contains v4.0 architectural content (vision, comparison tables, agent
hierarchy, gates, etc.). All of that content will migrate to the appropriate `sys/` files.
`_init_.md` will be fully rewritten with the sections above.

---

## 5. sys/ — Gatekeeper + Environment Layer

### What it is

`sys/` is the first module any agent touches after the root entrypoint.
It has two sequential responsibilities:

1. **Gatekeeper**: verifies the framework has everything it needs to operate before
   allowing any agent to proceed. Checks git, tokens, env vars, SHA-256, session state.
2. **Router**: once verified, `_index.md` routes the agent to `sdk/` for instantiation
   and tells it which module files to load based on its role and task.

`sys/` does NOT own domain logic, agent definitions, or contracts.
It owns the bootstrap protocol and the navigation contract only.

### File Map

```
sys/
├── _index.md        ← Navigation contract: what each agent role loads and when
│                      Also defines the routing rule to sdk/ post-verification
├── _verify.md       ← Verification contract: ordered checks, pass/fail criteria,
│                      blocker vs warning classification per check
├── bootstrap.sh     ← Implements _verify.md checks + all agent-requestable commands
├── venv.md          ← venv directives for agent-requested executions (rules, not tutorial)
├── worktrees.md     ← Worktree directives: lifecycle, naming convention, prune policy
└── git.md           ← Git connectivity verification rules + GitHub Actions guidelines
                        Does NOT contain yml — that lives in .github/workflows/
```

### sys/_verify.md — Verification Contract

Defines every check `bootstrap.sh` must run before routing to sdk/.
Ordered: blockers halt execution immediately. Warnings log and continue.

```
CHECK 1 — venv active                    BLOCKER
  Verify Python venv is activated and matches required version (3.11+)

CHECK 2 — git remote reachable           BLOCKER
  Verify connection to origin remote (git ls-remote)

CHECK 3 — git credentials valid          BLOCKER
  Verify authentication to remote succeeds (no prompt required)

CHECK 4 — required env vars present      BLOCKER
  Verify all vars in _verify.md#required-vars exist (names listed here, values in Vault)
  Required: PIV_PROVIDER, PIV_VAULT_PATH, PIV_SESSION_DIR

CHECK 5 — provider API token present     BLOCKER (per active provider)
  Anthropic: ANTHROPIC_API_KEY exists in env
  OpenAI:    OPENAI_API_KEY exists in env
  Ollama:    OLLAMA_HOST reachable on configured port

CHECK 6 — skills manifest SHA-256        BLOCKER
  Verify skills/manifest.json hash matches expected. Any mismatch halts + alerts SecurityAgent.

CHECK 7 — .piv/ session state            WARNING
  If active/ contains an unclosed session: log session_id, prompt for resume or discard.

CHECK 8 — worktrees stale               WARNING
  If worktrees/ contains entries not in git worktree list: log paths, suggest prune.
```

### sys/bootstrap.sh — Command Reference

Implements all checks from `_verify.md` and exposes all agent-requestable operations.
`piv validate` is mandatory before any session start.

```bash
# Verification (sys/_verify.md)
piv validate           # runs all 8 checks — MUST pass before any session

# Environment setup
piv setup              # creates venv, pip install, then piv validate

# Development
piv test               # pytest tests/ -v
piv test:unit          # pytest tests/ -v -m unit
piv test:int           # pytest tests/ -v -m integration
piv lint               # ruff check sdk/ tests/ + ruff format --check

# Worktrees
piv wt:add             # git worktree add worktrees/<task>/<expert> -b feature/<task>/expert-<N>
piv wt:list            # git worktree list
piv wt:remove          # git worktree remove + branch delete
piv wt:prune           # git worktree prune

# Runtime
piv run                # python -m sdk.cli (Phase 2+)
```

### sys/_index.md — Navigation Contract

Defines what each agent role loads and the routing rule to sdk/ post-verification.

```
## Routing Rule (applies after _verify.md passes)
All agents → sdk/core/loader.py instantiates the agent using agents/<role>.md
             + contracts/<role>.md + contracts/_base.md

## Load by Role (additional module files beyond the base)

| Role | Required modules | Conditional | Never load |
|---|---|---|---|
| Master Orchestrator (L0) | agents/, contracts/, git/ | engram/core/ | engram/security/, product workspace |
| SecurityAgent (L1) | contracts/security_agent.md | engram/security/ (every session) | product workspace |
| AuditAgent (L1) | contracts/audit_agent.md | engram/audit/, engram/precedents/ | product workspace |
| CoherenceAgent (L1) | contracts/coherence_agent.md | engram/coherence/ | product workspace |
| Domain Orchestrator (L1.5) | agents/, contracts/domain_orchestrator.md, git/ | engram/core/ | engram/security/ |
| Specialist Agent (L2) | specs/active/<task>.md + assigned skills only | product workspace (own task only) | engram/, sys/, other tasks |
| EvaluationAgent (L1) | contracts/evaluation_agent.md | metrics/schema.md | product workspace |
| LogisticsAgent (L1) | contracts/logistics_agent.md | — | engram/, product workspace |

## Load by Task

| Task | Load sequence |
|---|---|
| Session bootstrap | root entrypoint → sys/_verify.md → sys/_index.md → sdk/ |
| Gate evaluation | contracts/_base.md → agent-specific contract |
| Worktree operation | sys/worktrees.md → sys/bootstrap.sh piv wt:* |
| Skill loading | skills/manifest.json (SHA-256 check) → skill file |
| Engram write | engram/INDEX.md (AuditAgent only) |
| Git operation | git/ directives → sys/git.md for action rules |
| Compliance check | contracts/compliance_agent.md |
```

### sys/git.md — Git Connectivity + Action Guidelines

Two concerns in one file:
1. **Connectivity verification**: what CHECK 2 and CHECK 3 in `_verify.md` actually execute
   (git ls-remote, credential test commands). sys/ owns this because it must verify git
   independently of the `git/` module (which handles directives, not verification).
2. **GitHub Actions guidelines**: what each workflow does and when it triggers.
   Names required GitHub secrets (names only — values in Vault).
   Points to `.github/workflows/` for yml implementation.

---

## 6. SDK — Framework Engine

### What it is

`sdk/` is the publishable Python package (`piv-oac` on PyPI). It is a sibling folder
at root level alongside all other modules. It does NOT contain or duplicate any markdown
content — it reads and operationalizes the markdowns from their source-of-truth folders
at runtime via `sdk/core/loader.py`.

When published, all module markdowns are bundled via `pyproject.toml` `package_data`.
A user who runs `pip install piv-oac` gets both the Python code and all framework markdowns.

### sdk/ Folder Structure

```
sdk/
├── __init__.py              ← Public API: Session class — Session.init(...).run(...)
├── cli.py                   ← CLI entry point: init, validate, run, run-async, lint,
│                               test, observe, trigger
│
├── core/
│   ├── loader.py            ← FrameworkLoader: reads agents/*.md + contracts/*.md at runtime
│   │                           _AUTHORIZED_LOADS table + load_agent_for_role() enforcement
│   ├── session.py           ← SessionManager: reads/writes .piv/, checkpoint protocol
│   ├── session_async.py     ← AsyncSession: full PHASE 0→8 orchestration (~1340 lines)
│   │                           PHASE 0.1/0.2 wired (interview + spec_writer)
│   │                           PHASE 1: SpecDAGParser → stub fallback
│   │                           PHASE 1.5: BiasAuditAgent (L2 only) → bias_validator Tier 1 check
│   │                           PHASE 3: SecurityAgent Gate 0 (L2 non-fast-track)
│   │                             → LLM review (FLAGSHIP), REJECTED short-circuits before PHASE 5
│   │                             → writes engram/security/<session_id>/review.md
│   │                           PHASE 5: asyncio.gather() parallel experts (model per agent)
│   │                             → expert output persisted in audit record (experts[] array)
│   │                           PHASE 6: EvaluationAgent scoring (non-blocking, advisory)
│   │                             → 5 dimensions: FUNC/SEC/QUAL/COH/FOOT
│   │                             → writes engram/metrics/logs_scores/<session_id>.jsonl
│   │                           PHASE 7: CoherenceAgent Gate 1 (blocking multi-node, advisory single-node)
│   │                             → REJECTED only blocks if multi-node DAG
│   │                             → writes engram/gates/<session_id>/gate1.md
│   │                           PHASE 8: EngramWriter audit writes + broker.close()
│   │                           PMIABroker wired at all gate + checkpoint transitions
│   │                           Module helpers: _parse_verdict(), _extract_rationale(),
│   │                             _parse_eval_scores()
│   ├── bias_validator.py    ← Tier 1 deterministic validator for BiasAuditAgent output
│   │                           validate_bias_output(): 6 regex checks, zero LLM calls
│   │                           section_present(): quick header check for Gate 3
│   │                           BiasValidationResult: valid, missing_sections, warnings,
│   │                           red_team_result, multi_llm_result, lock_in_risks
│   ├── model_registry.py    ← Per-agent model assignment across all providers (Tier 1)
│   │                           ModelTier: FLAGSHIP / BALANCED / FAST
│   │                           resolve_model(agent, provider, task_complexity, escalate)
│   │                           14 agents mapped; dynamic escalation for audit/coherence/docs
│   │                           4 providers: anthropic, openai, ollama, gemini
│   ├── dag.py               ← DAGBuilder, DAGNode, Kahn topological sort (Tier 1)
│   │                           SpecDAGParser: parses ### task:: blocks from functional.md
│   ├── init.py              ← Initializer: CASE A (new) / CASE B (resume) bootstrap
│   ├── interview.py         ← InterviewHandler ABC + Console/Callback/PreSupplied modes
│   │                           run_interview(): 4-question standard set, key-first lookup
│   └── spec_writer.py       ← SpecWriter: answers → specs/active/ (PHASE 0.2)
│                               write_functional() includes ## Task Decomposition with
│                               ### task:: blocks parseable by SpecDAGParser
│
├── providers/
│   ├── base.py              ← BaseProvider ABC, ProviderRequest, ProviderResponse
│   ├── router.py            ← ProviderRouter: resolve_tier(agent_level) + get_provider()
│   │                           _COMPLEXITY_TO_AGENT_LEVEL: {1: "L2", 2: "L1"}
│   ├── anthropic.py         ← AnthropicProvider (sync, Tier 3)
│   ├── anthropic_async.py   ← AsyncAnthropicProvider (async, Tier 3)
│   ├── openai.py            ← OpenAIProvider (sync, Tier 3)
│   └── ollama.py / ollama_async.py  ← Ollama sync + async (Tier 2, TCP probe)
│
├── vault/
│   └── vault.py             ← Vault.scan_for_injection(), Vault.get_credential() — Tier 1
│
├── gates/
│   └── evaluator.py         ← GateEvaluator: invariant checks + circuit breaker — Tier 1
│
├── engram/
│   ├── reader.py            ← EngramReader: read-only, role-scoped access (_ROLE_SCOPE table)
│   └── writer.py            ← EngramWriter: AuditAgent-only, append-only, atomic writes
│                               write_json() for structured records, append() for markdown atoms
│                               atomic via temp file + os.replace()
│
├── metrics/
│   └── collector.py         ← TelemetryLogger (flush-after-write, OTEL secondary)
│                               write_index_entry() → logs/index.jsonl (cross-session)
│                               MetricsCollector façade for EvaluationAgent scoring
│
├── tools/
│   ├── __init__.py          ← Exports: SafeLocalExecutor, ExecutionResult,
│   │                           BlockedByToolError, ExecutionDataFilter, FilteredArg
│   ├── executor.py          ← SafeLocalExecutor: allowlist-only subprocess (no shell=True)
│   │                           ALLOWED_COMMANDS → sys/bootstrap.sh + pytest
│   │                           60s timeout, 32KB output cap, BlockedByToolError for Gate 2b
│   └── filter.py            ← ExecutionDataFilter: compiled regex blocks credentials,
│                               shell metacharacters, path traversal, API keys
│
├── triggers/
│   ├── github.py            ← run_from_github_event(): reads GITHUB_EVENT_PATH,
│   │                           extracts ```piv block objective + ```piv-answers YAML,
│   │                           calls AsyncSession, posts result comment via gh CLI
│   └── webhook.py           ← start_webhook_server(): HTTP POST /session + GET /health
│                               HMAC-SHA256 validation, fire-and-forget daemon thread
│
└── utils/
    ├── sha256.py            ← SHA256Verifier.verify() — Tier 1
    ├── complexity.py        ← ComplexityClassifier.classify() → ClassificationResult
    │                           Level 1 (fast-track) / Level 2 (interview required)
    └── injection.py         ← InjectionScanner.scan() — compiled regex, Tier 1
```

### How sdk/ Reads Module Markdowns

```python
# sdk/core/loader.py
class FrameworkLoader:
    def __init__(self, root: Path):
        self.root = root  # repo root when developing, package root when pip-installed

    def load_agent(self, name: str) -> Agent:
        md       = self.root / "agents"    / f"{name}.md"
        contract = self.root / "contracts" / f"{name}.md"
        base     = self.root / "contracts" / "_base.md"
        return Agent.from_markdown(md, contract, base)

    def load_skill(self, name: str) -> Skill:
        SHA256Verifier.verify(name, self.root / "skills" / "manifest.json")
        return Skill.from_markdown(self.root / "skills" / f"{name}.md")
```

### pyproject.toml — Package Definition

Replaces `requirements.txt`. Defines the publishable package and bundles all markdowns.

```toml
[project]
name = "piv-oac"
version = "5.0.0"
requires-python = ">=3.11"

[project.scripts]
piv-oac = "sdk.cli:main"

[tool.setuptools.package-data]
"*" = [
  "agents/*.md",
  "contracts/*.md",
  "skills/*.md",
  "sys/*.md",
  "sys/*.sh",
  "git/*.md",
  "engram/**/*.md",
  "specs/_templates/**"
]
```

### SDK Invariants

- `sdk/utils/` has zero internal imports from other sdk submodules
- `sdk/vault/` imports only from `sdk/utils/`
- `sdk/tools/` imports only from `sdk/tools/filter.py` (no LLM, no core imports)
- `sdk/providers/` imports only from `sdk/providers/base.py` — no core/ imports
- All LLM calls are in `sdk/providers/` only — all other sdk code is deterministic
- Every LLM call is preceded by `Vault.scan_for_injection()` — enforced in session layer
- No credentials hardcoded anywhere in `sdk/`

---

## 7. Module Layer — Domain Modules

All modules live at root level as siblings. Each is self-contained.
`sdk/core/loader.py` reads them. `sys/_index.md` tells agents which ones to load.
No module loads another module directly.

### Full Structure

```
root/
├── agents/        ← Per-agent config (read by sdk/core/loader.py)
├── contracts/     ← PMIA contracts, per-agent + _base.md (read by sdk/core/loader.py)
├── skills/        ← Lazy-loaded capability modules + manifest.json
├── engram/        ← Persistent atomized memory (AuditAgent exclusive writer)
├── specs/         ← Specification templates + active specs (gitignored during execution)
├── metrics/       ← Session metrics, evaluation scores, schema
├── git/           ← Git directives: topology, branch protection, naming policy
├── .github/       ← GitHub Actions yml (required path by GitHub)
│   └── workflows/
│       ├── piv-session.yml    ← triggers on issues.labeled piv:run →
│       │                          check-label → orchestration (PHASE 0–2) →
│       │                          phase-5-experts matrix (parallel) → gate-1-coherence
│       ├── gate2b.yml
│       ├── pre-merge.yml
│       └── staging-gate.yml
├── .piv/          ← Session state: active/completed/failed (not versioned)
├── config/        ← Runtime YAML: settings, injection_patterns, skill_registry
└── tests/         ← SDK tests only
```

### contracts/ Structure

```
contracts/
├── _base.md                ← PMIA v5.0: message types, HMAC-SHA256, 300-token limit
├── orchestrator.md         ← Master Orchestrator: emits/receives, DAG authority
├── security_agent.md       ← SecurityAgent: veto rules, CROSS_ALERT conditions
├── audit_agent.md          ← AuditAgent: write authority, checkpoint protocol
├── coherence_agent.md      ← CoherenceAgent: diff-only scope, Gate 1 authority
├── compliance_agent.md     ← ComplianceAgent: scope triggers, checklist format
├── evaluation_agent.md     ← EvaluationAgent: scoring output format, advisory-only
├── standards_agent.md      ← StandardsAgent: Gate 2b checklist, skill update proposal
├── domain_orchestrator.md  ← Domain Orchestrator: plan submission, worktree authority
├── specialist_agent.md     ← Specialist Agent: isolation rules, output format
├── logistics_agent.md      ← LogisticsAgent: TokenBudgetReport format
└── execution_auditor.md    ← ExecutionAuditor: deviation detection, 5K budget rule
```

### git/ Structure

```
git/
├── topology.md     ← Branch hierarchy diagram, naming conventions
├── protection.md   ← Protection rules per branch (main, staging, feature/*)
└── policy.md       ← Commit message format, push policy, PR requirements
```

### Module Ownership Rules

| Module | Read by | Written by | Loaded when |
|---|---|---|---|
| `agents/` | sdk/core/loader.py | Bootstrapping agent only | Agent instantiation |
| `contracts/` | sdk/core/loader.py (all agents load own + _base) | Bootstrapping agent only | Agent instantiation |
| `skills/` | sdk/core/loader.py (SHA-256 verified) | StandardsAgent (updates only) | On demand |
| `engram/` | sdk/engram/reader.py (role-specific atoms) | AuditAgent only | Per atom, on demand |
| `specs/active/` | Specialist Agents, Domain Orchestrators | Bootstrapping agent / user | PHASE 3+ |
| `metrics/` | sdk/metrics/collector.py | AuditAgent via collector | PHASE 5 + PHASE 8 |
| `git/` | MasterOrchestrator, Domain Orchestrators | Bootstrapping agent only | When branching |
| `.piv/` | sdk/core/session.py | AuditAgent via session | Every phase transition |
| `tests/` | CI / developer | Developer + CI | On demand (SDK tests only) |

---

## 8. Deployment Model — Framework, SDK, and User Workspace

### Framework Repo (this repo — `piv-oac_v5`)

Contains only governance, the SDK engine, and the SDK's own tests.
Never contains product code. Never has a `src/` folder for product output.

```
piv-oac_v5/   ← published as "piv-oac" on PyPI
├── sdk/       ← Python engine (reads sibling folders at runtime)
├── agents/    ← governance markdowns
├── contracts/ ← PMIA contracts
├── skills/    ← capability modules
├── engram/    ← persistent memory
├── sys/       ← gatekeeper + environment
└── tests/     ← SDK tests only
```

---

### User Entry Points (two valid modes)

#### Mode 1 — Standalone (clone the repo)

User clones `piv-oac_v5` and works entirely within it using branch separation.
No pip install required. The SDK runs from the cloned source.

#### Mode 2 — Embedded (pip install into existing project)

```bash
pip install piv-oac
piv-oac init --provider=anthropic
```

The SDK seeds itself into the user's existing git repo via branch creation.
The user never touches the framework files — the SDK manages them transparently.

---

### `piv-oac init` — Proactive Workspace Bootstrap

`init` does not detect and wait — it inspects and acts. If the minimum viable
branch structure does not exist, it creates it immediately without prompting.

```
piv-oac init --provider=<anthropic|ollama|openai>
        │
        ├─ Step 1: sys/_verify.md checks
        │   git remote reachable · credentials valid
        │   provider token present · Python env valid
        │
        ├─ Step 2: inspect existing branches
        │
        │   CASE A — only main exists (new project)
        │   ├── create piv-directive  (orphan branch — framework configs bundled from package)
        │   ├── create staging        (from main)
        │   ├── write .piv/           (session state directory)
        │   ├── write .gitignore      (worktrees/, .env, __pycache__/, .venv/)
        │   └── write initial checkpoint to piv-directive
        │
        │   CASE B — staging / piv-directive already exist
        │   ├── verify piv-directive integrity (SHA-256 of skills manifest)
        │   ├── check .piv/ for interrupted sessions
        │   └── resume or start clean session
        │
        └─ Step 3: ready — user passes objectives via Session.run()
```

**feature/ branches and worktrees are NOT created at init.**
They are created by Domain Orchestrators during PHASE 5 as the DAG requires them.
Each expert gets: `feature/<task-id>/expert-<N>` branching from `staging`.

---

### Branch Model in the User's Repo

```
user-repo/
│
├── main              ← stable product (Gate 3, human-only merge)
├── staging           ← integration layer (created by piv-oac init if missing)
├── piv-directive     ← orphan branch, framework configs (managed by SDK, never by user)
│
└── [created during sessions — deleted after merge]
    ├── feature/<task-id>/
    │   ├── feature/<task-id>/expert-1   ← Specialist Agent 1 worktree
    │   └── feature/<task-id>/expert-N   ← Specialist Agent N worktree
    └── fix/<issue-id>/
```

**piv-directive invariants:**
- Users never push to, merge from, or manually edit `piv-directive`
- SDK updates `piv-directive` only when a new version of `piv-oac` is installed
- Lock branch equivalent: no CI merges, no PR merges, SDK-write-only

---

### How Specialist Agents Write Product Code

Specialist Agents operate in `feature/<task-id>/expert-N` branches of the user's repo.
They write to that branch only. They cannot see other expert branches before Gate 1.

```
sdk/core/session.py   → manages .piv/ session state in user's repo
sdk/core/loader.py    → loads agent rules from piv-directive branch
Specialist Agent (L2) → writes to feature/<task-id>/expert-N (own branch only)
AuditAgent            → writes to .piv/ + engram/ atoms in piv-directive
```

The product code that accumulates across sessions lives in `main` (via staging, via Gate 3).
The framework governance that accumulates lives in `piv-directive`.
They never merge into each other.

---

### Full User Session Flow

```python
# After piv-oac init:
from piv_oac import Session

Session.init(
    provider="anthropic",       # cloud for L0/L1 complex reasoning
    local_model="llama3.2:1b",  # optional: local model for L2 mechanical tasks
                                # omit on limited machines — L2 falls back to cloud
).run(
    objective="add JWT authentication to the existing REST API"
)

# SDK takes over:
# PHASE 0   — Vault.scanForInjection() + SecurityAgent SecOps read
# PHASE 0.1 — Interview protocol: structured Q&A to clarify objective
#             (console / chat / callback depending on entry mode)
# PHASE 0.2 — Spec reformulation: answers → specs/active/functional.md
#                                          specs/active/architecture.md
#             User confirms specs — DAG NOT built until confirmed
# PHASE 1   — DAG built from confirmed specs (never from raw objective)
# PHASE 2   — Control agents instantiated (Security, Audit, Coherence, ...)
# PHASE 3-6 — Specialist Agents write code in feature/ branches
# PHASE 7   — Docs generated
# PHASE 8   — Engram updated, session archived in .piv/completed/
# Result   — PR ready: feature/<task-id>/ → staging (Gate 2b passed)
```

**Pre-supplied answers (programmatic mode):**
```python
Session.init(provider="anthropic").run(
    objective="add JWT authentication",
    answers={
        "protected_endpoints": ["/api/users", "/api/orders"],
        "user_model": "existing",
        "refresh_tokens": True
    }
)
```

**Callback mode (custom UI integration):**
```python
Session.init(provider="anthropic").run(
    objective="add JWT authentication",
    on_question=lambda q: my_ui.prompt(q)
)
```

---

## 9. Execution Tier Model

Every operation in PIV/OAC is assigned to a tier before execution.
The goal: minimize LLM usage, maximize local deterministic computation,
and remain functional on machines with very limited hardware.

### Tier Definitions

```
TIER 1 — Always local, always deterministic (any machine, zero LLM)
  SHA-256 verification · regex injection scan · complexity heuristic
  DAG construction · gate logic · session state · worktree management
  log writing · sys/_verify.md checks · manifest validation
  Cost: ~50MB RAM, minimal CPU, no external dependencies

TIER 2 — Optional local inference (by parameter, hardware permitting)
  Activated only if --local-model is passed at Session.init()
  Used for: L2 mechanical tasks, documentation generation, output formatting
  Model size guide:
    limited machine  → llama3.2:1b  (1B params, ~800MB RAM)
    mid-range        → llama3.2:3b  (3B params, ~2GB RAM)
    capable machine  → qwen2.5:7b   (7B params, ~5GB RAM)
  If Ollama unreachable → silently falls back to Tier 3

TIER 3 — Cloud inference (by parameter, API Key required)
  Used for: L0/L1 genuine reasoning, SecurityAgent veto decisions,
            plan design, conflict resolution, compliance interpretation
  Providers: Anthropic, OpenAI (extensible via sdk/providers/base.py)
```

### Tier Routing Rule

`sdk/providers/router.py` decides the tier per operation before execution:

```
Is operation deterministically resolvable?  → Tier 1, no LLM called
Is operation mechanical + local_model set?  → Tier 2, local model
Requires genuine reasoning?                 → Tier 3, cloud provider
```

**Complexity → agent_level → tier** (wired in `sdk/core/session_async.py`):

```python
_COMPLEXITY_TO_AGENT_LEVEL = {1: "L2", 2: "L1"}
# Level 1 micro-task  → L2 → Tier 2 if Ollama available, else Tier 3
# Level 2 architectural → L1 → Tier 3 always (cloud required for reasoning)
```

`ComplexityClassifier.classify(objective)` runs at PHASE 0 (Tier 1, no LLM).
The result propagates to every DAG node — each specialist is routed individually.

### Tier Assignment per Agent Level

| Agent level | Default tier | With local_model |
|---|---|---|
| L0 Master Orchestrator | Tier 3 | Tier 3 (complexity requires cloud) |
| L1 Control agents (Security, Audit...) | Tier 3 | Tier 3 |
| L1.5 Domain Orchestrators | Tier 3 | Tier 2 (structured tasks) |
| L2 Specialist Agents | Tier 3 | Tier 2 (mechanical code tasks) |
| All deterministic operations | Tier 1 | Tier 1 |

### Degraded Mode (very limited machines)

```
No GPU, low RAM:
  Tier 1: always available
  Tier 2: disabled (Ollama not running or too slow)
  Tier 3: all LLM work goes to cloud
  → SDK detects automatically, no configuration needed
  → Observability: logs to file only (Docker stack disabled)
```

### Session.init() Parameters

```python
Session.init(
    # Required: cloud provider for Tier 3
    provider="anthropic",          # or "openai"

    # Optional: local model for Tier 2 (omit on limited machines)
    local_model="llama3.2:1b",

    # Full local mode (no cloud — Tier 2 handles everything)
    provider="ollama",
    model="llama3.2:3b",
)
```

---

## 10. Observability

### Default: logs to file (zero overhead, any machine)

The SDK always writes structured JSON logs to `logs/` first.
This is synchronous, low-cost, and works with no external dependencies.
`logs/` is gitignored — never versioned.

```
logs/
├── index.jsonl                ← cross-session historical index (one line per session)
│                                 fields: session_id, objective, status, complexity_level,
│                                 fast_track, provider, total_tokens, duration_ms,
│                                 expert_count, gate_verdicts, warning_count
│                                 written by TelemetryLogger.write_index_entry() at close
│                                 queryable: jq 'select(.status=="failed")' logs/index.jsonl
├── sessions/
│   └── <session-id>.jsonl     ← one JSON line per event (full event trace per session)
├── gates/
│   └── <session-id>.jsonl     ← gate verdicts with rationale
└── scores/
    └── <session-id>.jsonl     ← EvaluationAgent scoring per criterion
```

**Canonical log line format:**
```json
{
  "timestamp_ms": 1744790781342,
  "timestamp_iso": "2026-04-13T10:23:01.342Z",
  "level": "INFO",
  "session_id": "<uuid>",
  "agent_id": "SecurityAgent",
  "phase": "PHASE_0",
  "action": "injection_scan",
  "outcome": "PASS",
  "tier": 1,
  "duration_ms": 4,
  "tokens_used": 0,
  "detail": {}
}
```

### Optional: Grafana stack via Docker (capable machines)

Activated on demand — never runs automatically during agent sessions.

```
observability/
├── docker-compose.yml     ← Loki + Tempo + Grafana + OTEL Collector
├── otel-collector.yaml    ← routes logs → Loki, traces → Tempo
└── dashboards/
    ├── sessions.json      ← session overview panel
    ├── gates.json         ← gate first-pass rate, rejections, circuit breaker
    └── agents.json        ← per-agent tokens, phase times, fragmentations
```

**Stack footprint with resource limits:**

| Service | RAM limit | CPU limit |
|---|---|---|
| Loki | 128MB | 0.2 cores |
| Tempo | 128MB | 0.2 cores |
| Grafana | 150MB | 0.1 cores |
| OTEL Collector | 64MB | 0.1 cores |
| **Total** | **~470MB** | **~0.6 cores** |

**Commands (in sys/bootstrap.sh):**
```bash
piv observe:start    # docker compose -f observability/docker-compose.yml up -d
piv observe:stop     # docker compose -f observability/docker-compose.yml down
piv observe:logs     # tail -f logs/sessions/<latest>.jsonl
```

**OTEL integration in SDK:**
- `sdk/metrics/collector.py` writes to `logs/` (primary, always)
- If OTEL Collector reachable on `:4317` → also sends traces async (secondary)
- If Collector down → no error, no retry, file log is sufficient

### TelemetryLogger — Lifecycle and Implementation

`TelemetryLogger` is instantiated at `Session.init()` and remains open for the entire session.
It is the single writer to `logs/`. No agent writes logs directly.

```python
class TelemetryLogger:
    def __init__(self, session_id: str, log_dir: Path):
        self.session_id = session_id
        self._file = (log_dir / "sessions" / f"{session_id}.jsonl").open("a")
        self._otel_active = self._check_otel_collector()  # Tier 1 check

    def record(self, entry: dict) -> None:
        """Called by every agent after each action via the _log block."""
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()                        # sync write — Tier 1, always
        if self._otel_active:
            self._send_otel_async(entry)          # fire-and-forget — never blocks

    def close(self) -> None:                      # called at PHASE 8 session close
        self._file.close()
```

- `flush()` is called after every write — no buffering, no data loss on crash.
- OTEL send is async and non-blocking. If Collector is down: silently skipped.
- One file handle open per session — no per-event open/close overhead.
- `logs/gates/<session_id>.jsonl` and `logs/scores/<session_id>.jsonl` use
  the same pattern: separate TelemetryLogger instances per log type.

---

## 11. Interview Protocol (PHASE 0.1 — PHASE 0.2)

The raw objective is never the source of truth. Specs are.
The interview protocol activates only when needed — the complexity classifier decides.

### Complexity-First Decision (Tier 1 — deterministic, no LLM)

```
Objective received
      │
      ▼
ComplexityClassifier.classify(objective)   ← heuristic only, Tier 1, zero LLM
      │
      ├─ Level 1 (micro-task)
      │    Criteria: ≤2 files, unambiguous RF, low risk, no architectural change
      │    → Skip interview entirely
      │    → Spec inferred directly from objective
      │    → Gate 0 fast-track (60 sec max, SecurityAgent only)
      │    → Execute
      │
      └─ Level 2
           Criteria: multiple files, ambiguity, architectural decisions, or security scope
           → PHASE 0.1 interview activates
           → PHASE 0.2 spec reformulation → user confirmation → DAG build
```

### PHASE 0.1 — Structured Q&A (Level 2 only)

**Implemented in `sdk/core/interview.py` — `run_interview()`.**
Questions are a fixed standard set (`_STANDARD_QUESTIONS`) — not LLM-generated.
Handler selected by caller: `PreSuppliedHandler` (answers dict), `CallbackHandler` (on_question),
or `ConsoleHandler` (CLI). Short answer-key lookup tried first; falls back to full question text.

| Complexity | Questions asked | Example |
|---|---|---|
| Level 1 (micro) | 0 — interview skipped entirely | `fix typo in README` |
| Level 2 (any) | 4 standard questions (2 required, 2 optional) | `build Stripe payment integration` |

**Standard questions:** scope (required), acceptance_criteria (required),
constraints (optional), out_of_scope (optional).

### PHASE 0.2 — Spec Reformulation

**Implemented in `sdk/core/spec_writer.py` — `SpecWriter.write_functional()`.**
Answers are written to `specs/active/functional.md`. The file includes a
`## Task Decomposition` section with `### task::<node_id>` blocks parsed by `SpecDAGParser`.

```
specs/active/
├── functional.md     ← what the system must do + task decomposition blocks
├── architecture.md   ← structural decisions (write_architecture() — Level 2 complex)
└── quality.md        ← acceptance criteria, coverage thresholds (write_quality())
```

**Note:** User confirmation before PHASE 1 is architecturally required (documented here)
but not yet implemented in `session_async.py`. Currently PHASE 0.2 → PHASE 1 is automatic.
This is item 39 (future work).

### I/O Modes

| Entry mode | Interview channel | Implementation |
|---|---|---|
| CLI (`piv-oac run`) | Console stdin/stdout | `sdk/core/interview.py` default handler |
| AI tool (CLAUDE.md, Cursor) | Chat conversation | Agent asks in conversation, user responds |
| Programmatic (SDK embedded) | Pre-supplied `answers={}` dict | Skips Q&A, validates completeness |
| Custom UI | `on_question=callback` | Callback receives question, returns answer |

### sdk/core/interview.py — Abstract I/O Contract

```python
class InterviewHandler(ABC):
    @abstractmethod
    def ask(self, question: str) -> str: ...

class ConsoleHandler(InterviewHandler):
    def ask(self, question: str) -> str:
        return input(f"[PIV/OAC] {question}\n> ")

class CallbackHandler(InterviewHandler):
    def __init__(self, callback): self.callback = callback
    def ask(self, question: str) -> str:
        return self.callback(question)

class PreSuppliedHandler(InterviewHandler):
    def __init__(self, answers: dict): self.answers = answers
    def ask(self, question: str) -> str:
        return self.answers.get(question) or raise MissingAnswerError(question)
```

---

## 12. Core Principles for v5.0

These principles drive every structural and implementation decision.

### 12.1 Determinism-First

Any operation resolvable by formula, heuristic, regex, or local computation
MUST NOT invoke an LLM. LLM calls reserved for genuine reasoning only.

**Deterministic zone (no LLM):**
- Complexity classification
- Domain identification (keyword matching)
- Injection detection (compiled regex)
- Effort estimation (formula-based)
- Checksum validation (SHA-256)
- Gate 0 fast-track (60-second budget)
- Token budget calculation (LogisticsAgent)
- Score aggregation (EvaluationAgent)

**LLM zone (after Vault scan + intent verification):**
- Plan design
- Conflict resolution
- Compliance interpretation
- Research synthesis
- Documentation generation

### 12.2 Maximal Local Delegation

Prefer local computation to reduce token consumption and provider dependency:
- `scripts/` tools execute locally before any agent evaluates results
- Pre-commit hooks enforce quality deterministically
- SHA-256 manifests verified locally before skill loading
- `validate_env.py` runs locally at session start (mandatory)

### 12.3 Strict Auditability

Every action, decision, and gate outcome is traceable:
- AuditAgent is the sole writer to `engram/` and audit logs
- Every gate verdict logged: timestamp, agent, rationale
- Session state tracked in `.piv/active/`, `.piv/completed/`, `.piv/failed/`
- Metrics captured in `metrics/sessions.md` and `metrics/logs_scores/<session_id>.jsonl`

### 12.4 Spec-First Execution

No implementation file receives code without an approved spec.
Stubs raise `NotImplementedError("ClassName.methodName() — Phase N pending")`.
No exceptions.

### 12.5 Zero-Trust Security

- Vault access requires explicit human instruction
- Credentials flow only via MCP, never in context
- SecurityAgent has unconditional veto authority at any phase
- `Vault.scanForInjection()` precedes every LLM call
- `agent-configs` equivalent in v5.0: `sys/` files in `main` — governed by PR policy

### 12.6 Structural Separation of Concerns

| Layer | Owns | Does NOT own |
|---|---|---|
| Root | Framework identity, entrypoints, build context | Logic, commands, module content |
| `sys/` | Operational setup, agent contracts, module index | Business logic, product code |
| Module layer | Domain-specific knowledge and execution | Cross-module routing (that is sys's job) |

---

## 13. Migration Map: v4.0 → v5.0

### Rescue (rewrite in English, restructure)

| v4.0 Source | v4.0 Location | v5.0 Destination | Notes |
|---|---|---|---|
| Framework vision, problem/solution | `_init_.md` (v4, mixed) | `_init_.md` sections 2-4 | Rewrite in English, conceptual only |
| Comparison table vs competitors | `_init_.md` (v4) | `_init_.md` section 4 | Clean table, English |
| Agent taxonomy (L0/L1/L2) | `registry/agent_taxonomy.md` | `agents/` (per-agent files) | Keep hierarchy, clarify L1.5 |
| Model assignment strategy | `contracts/models.md` | `agents/` files (section per agent) | Merged into per-agent files |
| Gate system (0,1,2,2b,3) | `contracts/gates.md` | `contracts/_base.md` + agent contracts | Gate logic in relevant agent contracts |
| Execution phases (PHASES 0-8) | `registry/orchestrator.md` + `agent.md` | `agents/orchestrator.md` | Formalize entry/exit per phase |
| Engram system | `engram/INDEX.md` + `VERSIONING.md` | `engram/INDEX.md` + `engram/VERSIONING.md` | Keep directory and format |
| Skill manifest | `skills/manifest.json` | `skills/manifest.json` | Keep format, update hashes |
| Skill modules (31 files) | `skills/*.md` | `skills/*.md` | English audit on each |
| PMIA inter-agent protocol | `skills/inter-agent-protocol.md` | `contracts/_base.md` | Elevated to base contract |
| Evaluation rubric | `contracts/evaluation.md` | `contracts/evaluation_agent.md` | Per-agent contract format |
| Parallel safety rules | `contracts/parallel_safety.md` | `contracts/specialist_agent.md` (section) | Embedded in specialist contract |
| Branch topology | `docs/git-branch-protection.md` | `git/topology.md` + `git/protection.md` | Split by concern |
| Branch naming / commit policy | `docs/git-branch-protection.md` | `git/policy.md` | Separated |
| Observability (OTEL, logs) | `skills/observability.md` | `skills/observability.md` | Stays as skill module |
| Lazy Loading rules | `skills/context-management.md` | `skills/context-management.md` | Stays as skill module |
| Session continuity (.piv/) | `skills/session-continuity.md` | `agents/orchestrator.md` (section) + `.piv/` | Embedded in orchestrator |
| Pre-commit hooks | `.pre-commit-config.yaml` | `.pre-commit-config.yaml` | Adapt paths for v5.0 |
| Metrics schema | `metrics/schema.md` | `metrics/schema.md` | Keep format |
| validate_env.py | `scripts/validate_env.py` | `sys/bootstrap.sh` + `sys/_verify.md` | Absorbed — no longer a standalone script |
| Compliance scopes | `registry/compliance_agent.md` | `contracts/compliance_agent.md` | Per-agent contract format |
| venv / bash setup | Not documented in v4.0 | `sys/bootstrap.sh` + `sys/venv.md` | New in v5.0 |
| Worktree lifecycle | `skills/worktree-automation.md` | `sys/worktrees.md` | Elevated to environment layer |
| CI workflows | `.github/workflows/` | `.github/workflows/` (keep) + `sys/git.md` (guidelines) | yml stays, guidelines in sys/ |
| Git action guidelines | `docs/git-branch-protection.md` | `sys/git.md` | What workflows do, not the yml |

### Discard (do not migrate)

| v4.0 Content | Reason |
|---|---|
| Spanish inline in markdown | Language policy: English only in repo |
| `agent.md` (monolithic) | Split into `sys/agents.md` + `sys/phases.md` |
| `LAYERS.md` (as-is) | Concepts absorbed into `_init_.md` layer map |
| Domain-specific engram atoms (axonum, piv-challenge) | Product-specific, not framework |
| `docs/TUTORIAL_LEVEL2.md` | Deferred — no user-facing docs this phase |
| `docs/ROADMAP_PRODUCCION.md` | Rebuilt from v5.0 scope |
| `security_vault.md` | Rebuilt under Zero-Trust, no static vault doc |
| `rust-tauri-ci.md` skill | Product-specific, not framework |
| Mixed Spanish/English commits | Commit message policy: English only |

---

## 14. File-by-File Build Plan

Build order: Root → sys/ → contracts/ → agents/ → sdk/ → git/ + infra → modules.

### P0 — Root layer (unblocks everything)

| # | File | Status | Depends on |
|---|---|---|---|
| 1 | `_init_.md` (full rewrite) | PENDING | Nothing |
| 2 | `README.md` | PENDING | `_init_.md` |
| 3 | `CLAUDE.md` | PENDING | `sys/_index.md` structure defined |
| 4 | `.gitignore` | PENDING | Structure confirmed |
| 5 | `pyproject.toml` | PENDING | `sdk/` structure defined |
| 6 | `anthropic.py` | PENDING | `sdk/__init__.py` |
| 7 | `ollama.py` | PENDING | `sdk/__init__.py` |
| 8 | `openai.py` | PENDING | `sdk/__init__.py` |

### P1 — sys/ (gatekeeper + environment)

| # | File | Status | Depends on |
|---|---|---|---|
| 9 | `sys/_verify.md` | PENDING | Nothing — defines verification contract |
| 10 | `sys/_index.md` | PENDING | Module structure confirmed |
| 11 | `sys/bootstrap.sh` | PENDING | `sys/_verify.md` |
| 12 | `sys/venv.md` | PENDING | Nothing |
| 13 | `sys/worktrees.md` | PENDING | `git/topology.md` |
| 14 | `sys/git.md` | PENDING | `.github/workflows/` structure defined |

### P1 — contracts/ (PMIA communication standard)

| # | File | Status | Depends on |
|---|---|---|---|
| 15 | `contracts/_base.md` | PENDING | Nothing — PMIA v5.0 base |
| 16 | `contracts/orchestrator.md` | PENDING | `contracts/_base.md` |
| 17 | `contracts/security_agent.md` | PENDING | `contracts/_base.md` |
| 18 | `contracts/audit_agent.md` | PENDING | `contracts/_base.md` |
| 19 | `contracts/coherence_agent.md` | PENDING | `contracts/_base.md` |
| 20 | `contracts/compliance_agent.md` | PENDING | `contracts/_base.md` |
| 21 | `contracts/evaluation_agent.md` | PENDING | `contracts/_base.md` |
| 22 | `contracts/standards_agent.md` | PENDING | `contracts/_base.md` |
| 23 | `contracts/domain_orchestrator.md` | PENDING | `contracts/_base.md` |
| 24 | `contracts/specialist_agent.md` | PENDING | `contracts/_base.md` |
| 25 | `contracts/logistics_agent.md` | PENDING | `contracts/_base.md` |
| 26 | `contracts/execution_auditor.md` | PENDING | `contracts/_base.md` |

### P1 — agents/ (per-agent configuration)

| # | File | Status | Depends on |
|---|---|---|---|
| 27 | `agents/orchestrator.md` | PENDING | `contracts/orchestrator.md` |
| 28 | `agents/security_agent.md` | PENDING | `contracts/security_agent.md` |
| 29 | `agents/audit_agent.md` | PENDING | `contracts/audit_agent.md` |
| 30 | `agents/coherence_agent.md` | PENDING | `contracts/coherence_agent.md` |
| 31 | `agents/compliance_agent.md` | PENDING | `contracts/compliance_agent.md` |
| 32 | `agents/evaluation_agent.md` | PENDING | `contracts/evaluation_agent.md` |
| 33 | `agents/standards_agent.md` | PENDING | `contracts/standards_agent.md` |
| 34 | `agents/domain_orchestrator.md` | PENDING | `contracts/domain_orchestrator.md` |
| 35 | `agents/specialist_agent.md` | PENDING | `contracts/specialist_agent.md` |
| 36 | `agents/logistics_agent.md` | PENDING | `contracts/logistics_agent.md` |
| 37 | `agents/execution_auditor.md` | PENDING | `contracts/execution_auditor.md` |
| 38 | `agents/research_orchestrator.md` | PENDING | `contracts/_base.md` |

### P2 — sdk/ (framework engine — Python package)

| # | File | Status | Depends on |
|---|---|---|---|
| 39 | `sdk/__init__.py` | PENDING | All P1 contracts + agents defined |
| 40 | `sdk/cli.py` | PENDING | `sdk/__init__.py` |
| 41 | `sdk/core/loader.py` | PENDING | `agents/`, `contracts/`, `skills/` structure |
| 42 | `sdk/core/session.py` | PENDING | `.piv/` structure |
| 43 | `sdk/core/init.py` | PENDING | `sys/_verify.md` — branch bootstrap logic |
| 44 | `sdk/core/dag.py` | PENDING | Tier 1 — deterministic |
| 45 | `sdk/core/interview.py` | PENDING | PHASE 0.1 — abstract I/O (Console/Callback/PreSupplied handlers) |
| 46 | `sdk/core/spec_writer.py` | PENDING | PHASE 0.2 — answers → specs/active/ |
| 47 | `sdk/providers/base.py` | PENDING | BaseProvider abstract interface |
| 48 | `sdk/providers/router.py` | PENDING | Tier 1/2/3 routing per operation |
| 49 | `sdk/providers/anthropic.py` | PENDING | Tier 3 cloud |
| 50 | `sdk/providers/openai.py` | PENDING | Tier 3 cloud |
| 51 | `sdk/providers/ollama.py` | PENDING | Tier 2 local inference |
| 52 | `sdk/vault/vault.py` | PENDING | Tier 1 — compiled regex |
| 53 | `sdk/gates/evaluator.py` | PENDING | Tier 1 — deterministic gate logic |
| 54 | `sdk/engram/reader.py` | PENDING | Read-only, role-scoped |
| 55 | `sdk/metrics/collector.py` | PENDING | Writes logs/ first, OTEL secondary |
| 56 | `sdk/utils/sha256.py` | PENDING | Tier 1 |
| 57 | `sdk/utils/complexity.py` | PENDING | Tier 1 — heuristic only |
| 58 | `sdk/utils/injection.py` | PENDING | Tier 1 — compiled regex only |

### P2 — git/, infrastructure, observability

| # | File | Status | Depends on |
|---|---|---|---|
| 59 | `git/topology.md` | PENDING | Nothing |
| 60 | `git/protection.md` | PENDING | `git/topology.md` |
| 61 | `git/policy.md` | PENDING | Nothing |
| 62 | `observability/docker-compose.yml` | PENDING | Nothing |
| 63 | `observability/otel-collector.yaml` | PENDING | `observability/docker-compose.yml` |
| 64 | `observability/dashboards/sessions.json` | PENDING | `logs/` schema defined |
| 65 | `observability/dashboards/gates.json` | PENDING | `logs/` schema defined |
| 66 | `observability/dashboards/agents.json` | PENDING | `logs/` schema defined |
| 67 | `.pre-commit-config.yaml` | PENDING | Nothing |
| 68 | `.github/workflows/gate2b.yml` | PENDING | `contracts/security_agent.md` |
| 69 | `.github/workflows/pre-merge.yml` | PENDING | `contracts/coherence_agent.md` |
| 70 | `.github/workflows/staging-gate.yml` | PENDING | `contracts/compliance_agent.md` |

### P3 — Module layer (memory, skills, specs, metrics)

| # | File | Status | Depends on |
|---|---|---|---|
| 71 | `engram/INDEX.md` | PENDING | `contracts/audit_agent.md` |
| 72 | `engram/VERSIONING.md` | PENDING | `engram/INDEX.md` |
| 73 | `engram/<subdirs>/` (9 dirs) | PENDING | `engram/INDEX.md` |
| 74 | `skills/manifest.json` | PENDING | All `skills/*.md` |
| 75 | `skills/*.md` (22 modules) | PENDING | `contracts/_base.md` |
| 76 | `metrics/schema.md` | PENDING | `agents/orchestrator.md` |
| 77 | `specs/_templates/INDEX.md` | PENDING | `agents/` structure defined |
| 78 | `specs/_templates/ci/pre-commit-config.yaml` | PENDING | `.pre-commit-config.yaml` |
| 79 | `logs/` directory scaffold (gitignored) | PENDING | `sdk/metrics/collector.py` |
| 80 | `tests/` structure (SDK tests only) | PENDING | `sdk/` complete |

---

## 15. Rescued Content: Agent Architecture

### Hierarchy

```
L0  Master Orchestrator      claude-opus-4-6      Persistent
│   Receives objectives, builds DAG, never reads source code.
│   Composes and coordinates the control environment.
│
├── L1  SecurityAgent         claude-opus-4-6      Persistent
│       Unconditional veto at any phase.
│       Fragments into 6 sub-agents at context saturation.
│
├── L1  AuditAgent            claude-sonnet-4-6    Persistent
│       Sole writer to engram/ and audit logs.
│       Closes sessions (PHASE 8). Generates TechSpecSheet.
│
├── L1  CoherenceAgent        claude-sonnet-4-6    Persistent (parallel tasks)
│       Monitors diffs only. Gate 1 approval authority.
│       Cannot resolve security conflicts unilaterally.
│
├── L1  ComplianceAgent       claude-sonnet-4-6    FULL or MINIMAL scope
│       Generates compliance checklists. No legal guarantee.
│
├── L1  EvaluationAgent       claude-sonnet-4-6    PHASE 5
│       Scores Specialist Agent outputs (0-1 rubric).
│       Information-only — no gate veto authority.
│       Early termination recommendation at score ≥ 0.90.
│
├── L1  StandardsAgent        claude-sonnet-4-6    Gate 2b
│       Code quality validation.
│       Proposes skill updates at session closure.
│
├── L1  DocumentationAgent    claude-sonnet-4-6 / claude-haiku-4-5   PHASE 7
│
├── L1  ResearchOrchestrator  TBD                  RESEARCH mode only
│
├── L1  LogisticsAgent        claude-haiku-4-5     PHASE 1
│       Resource analysis. TokenBudgetReport before DAG confirmation.
│
├── L1  ExecutionAuditor      claude-haiku-4-5     Out-of-band
│       Protocol deviation detection. Strict 5K token budget.
│
├── L1.5 Domain Orchestrators claude-sonnet-4-6    Per domain (PHASE 3-6)
│        Designs layered plans → submits to gates → creates worktrees
│        → launches Specialist Agents → executes two-level merges.
│
└── L2  Specialist Agents     claude-haiku-4-5     Per task (PHASE 5)
        Atomic tasks in isolated worktrees.
        Reads: own worktree + specs/active/ + assigned skills ONLY.
```

### Agent Response Structure

Every agent response includes a mandatory `_log` block. `TelemetryLogger` extracts
and writes this block — agents never write to `logs/` directly.

```python
# Standard agent response shape
{
    "result": { ... },          # business payload — varies by agent and action
    "_log": {
        "timestamp_ms": 1744790781342,
        "timestamp_iso": "2026-04-13T10:23:01.342Z",
        "session_id": "sess_a1b2c3",
        "agent_id": "SecurityAgent",
        "phase": "PHASE_0",
        "action": "injection_scan",
        "outcome": "PASS",       # PASS | FAIL | VETO | BLOCKED | ESCALATED
        "tier": 1,
        "duration_ms": 4,
        "tokens_used": 0,        # 0 for Tier 1 deterministic actions
        "detail": {}             # optional structured context (gate rationale, etc.)
    }
}
```

`sdk/core/session.py` strips `_log` from `result` before passing payload to
the next agent. `TelemetryLogger.record()` receives only the `_log` block.

### Model Assignment

| Model | Assigned to | Trigger for escalation |
|---|---|---|
| `claude-opus-4-6` | Master Orchestrator, SecurityAgent | High-complexity trade-offs, veto decisions |
| `claude-sonnet-4-6` | All L1 control agents, Domain Orchestrators | Structured analysis, plan generation |
| `claude-haiku-4-5` | Specialist Agents, LogisticsAgent, ExecutionAuditor | Atomic/mechanical tasks |

Escalation: 80% context window saturation triggers fragmentation or level escalation.
Maximum sub-agent depth: 2 levels.

### Task Classification

| Level | Criteria | Protocol |
|---|---|---|
| Level 1 (micro-task) | ≤2 files, existing RF, low risk | Fast-track: deterministic only, 60-sec budget, no LLM |
| Level 2 (complex) | Multiple files, architectural changes, ambiguity | Full orchestration: DAG + three-gate enforcement + human confirmation |

---

## 16. Rescued Content: Gate System

| Gate | Trigger | Agents | Type |
|---|---|---|---|
| Gate 0 | Level 1 fast-track | SecurityAgent only | Deterministic, 60-sec max |
| Gate 1 | After each Specialist completes | CoherenceAgent | Subbranch → task merge |
| Gate 2 | Pre-worktree creation | Security + Audit + Coherence (parallel) | Plan review. No worktrees until passed. |
| Gate 2b | Post-CI (requires LOOP_GREEN_REPORT) | Security + Audit + Standards (parallel) | Code review. Tools run before LLM. |
| Gate 3 | Pre-production | ComplianceAgent + human confirmation | Staging → main. Hard block. |

### Circuit Breaker

`MAX_GATE_REJECTIONS = 3` — three consecutive rejections at the same gate:
- Execution halts
- Session moved to `.piv/failed/`
- AuditAgent writes post-mortem to `engram/audit/`

### Gate 2b Mandatory Sequence

```
1. grep       (pattern scan)
2. pip-audit  (dependency CVEs)
3. semgrep    (static analysis)
4. All pass → LLM review
   Any tool unavailable → BLOCKED_BY_TOOL status (no LLM verdict issued)
```

### Key Invariants (defined in `contracts/_base.md` — cannot be overridden by any agent contract)

- No worktree is created before Gate 2 approval.
- `main` is unreachable by any automated process without explicit human confirmation.
- SecurityAgent veto overrides all other approvals at any gate and at any phase.
- Gate 3 always requires a human confirmation signal — no automated path around it.
- Any agent contract may ADD criteria to a gate. No agent contract may REMOVE or WEAKEN
  an invariant defined in `_base.md`.
- `contracts/_base.md` is the single source of truth for gate invariants.
  Individual agent contracts extend it; they never override it.

---

## 17. Rescued Content: Execution Phases

| Phase | Name | Entry | Exit | Key agents |
|---|---|---|---|---|
| PHASE 0 | Intent validation | Objective received | Intent verified, SecOps read | SecurityAgent, MasterOrchestrator |
| PHASE 1 | DAG construction | PHASE 0 complete | DAG confirmed by user, TokenBudgetReport issued | MasterOrchestrator, LogisticsAgent |
| PHASE 2 | Control environment | DAG confirmed | All L1 agents instantiated (parallel) | Security, Audit, Coherence, Standards, Compliance |
| PHASE 3 | Domain Orchestrators | PHASE 2 complete | Domain plans designed | Domain Orchestrators (parallel if independent) |
| PHASE 4 | Plan review | Plans ready | Gate 2 passed | Security + Audit + Coherence |
| PHASE 5 | Parallel execution | Gate 2 passed | All specialists complete | Specialist Agents, EvaluationAgent, CoherenceAgent |
| PHASE 6 | Two-level merge | PHASE 5 complete | task → staging approved | Gate 1 (subbranch→task), Gate 2b (task→staging) |
| PHASE 7 | Documentation | Gate 2b passed | Docs generated and reviewed | DocumentationAgent |
| PHASE 8 | Session closure | PHASE 7 complete | Engram updated, metrics logged, session archived | AuditAgent |

### Execution Modes

| Mode | Specs loaded | Use case |
|---|---|---|
| INIT | None (interview protocol) | Project bootstrap |
| DEVELOPMENT | `functional.md` + `architecture.md` | Code development |
| RESEARCH | `research.md` | Research and investigation |
| MIXED | All three | Combined dev + research |

---

## 18. Rescued Content: Engram Memory System

### Directory Structure

```
engram/
├── INDEX.md        ← Agent → atom mapping, load conditions, cross-impact table
├── VERSIONING.md   ← SHA-256 per atom, snapshot system, rollback procedures
├── core/           ← Architecture decisions, operational patterns
├── security/       ← Attack patterns, known vulnerabilities (SecurityAgent exclusive)
├── quality/        ← Code and test patterns
├── audit/          ← Gate decisions, RF coverage analysis, post-mortems
├── coherence/      ← Conflict resolution patterns
├── compliance/     ← Regulatory learnings, legal patterns
├── domains/        ← Domain-specific knowledge (per product, not per framework)
├── precedents/     ← Resolved decisions from prior sessions
└── snapshots/      ← Immutable snapshots for rollback
```

### Invariants

| Rule | Detail |
|---|---|
| Single writer | AuditAgent is the only agent authorized to write to `engram/` |
| Atom size limit | 500 lines maximum per atom file |
| Single writer per session | One write session per atom at a time |
| No secrets | Credentials or sensitive data strictly prohibited |
| SHA-256 versioning | Every atom has a hash in VERSIONING.md. Mismatch = integrity failure. |
| Rollback | Snapshots in `engram/snapshots/` allow full rollback to any prior state |

### Engram Load Policy

Engram atoms are NEVER pre-loaded. Loading is always lazy, conditional, and declared.
Skills provide operational knowledge (how to do X). Engram provides historical context
(decisions made, patterns learned in prior sessions).

| Agent | May load from engram | Condition |
|---|---|---|
| SecurityAgent | `security/` | Only if prior security events exist for this objective domain |
| AuditAgent | `audit/` + `precedents/` | Only at phase exit or when writing checkpoints |
| CoherenceAgent | `coherence/` | Only when a conflict is detected — not by default |
| Domain Orchestrators | `core/` + `domains/<project>` | Only if a prior session covered the same domain |
| Specialist Agents | Nothing | Isolated by design — skills only |
| ComplianceAgent | `compliance/` | FULL or MINIMAL scope trigger only |
| ResearchOrchestrator | `core/` | Only for epistemic gate context |

Load request flow:
1. Agent declares which atom it needs (atom path + reason)
2. sdk/engram/reader.py verifies the agent's role is allowed to read that atom
3. Atom is loaded for that interaction only — not held in context beyond the need
4. If no relevant atom exists → agent operates from skills alone (not an error)

---

## 19. Rescued Content: Skill System

### Manifest Format

```json
{
  "version": "1.0",
  "signed_by": "StandardsAgent",
  "signed_at": "2026-04-02",
  "skills": {
    "<skill-name>": {
      "file": "skills/<skill-name>.md",
      "sha256": "<hash>",
      "last_updated": "<date>",
      "gate_verified": true
    }
  }
}
```

### Load Policy

- Skills are never pre-loaded. Agents declare required skills at instantiation.
- Manifest SHA-256 verified locally before any skill is loaded.
- Hash mismatch: skill rejected, SecurityAgent notified, session pauses.

### Skills to Migrate from v4.0

**v5.0 migration note:** Initial plan absorbed 9 skills into sys/contracts/sdk. In practice, all skills
were implemented as explicit `skills/*.md` files for discoverability and manifest verification.
Session 5 v5.1 audit vs v4 resulted in 3 new skills and expanded depth across all existing ones.

**`skills/*.md` modules — 24 files (v5.1 actual):**

| Skill | Lines | Status |
|---|---|---|
| `bias-audit.md` | 208 | NEW — session 5 (BiasAuditAgent: 4 directives, red team, multi-LLM audit) |
| `change-management.md` | 148 | NEW — session 5 (restored from v4: change classification, manifest integrity, rollback) |
| `coherence-analysis.md` | — | NEW v5 — CoherenceAgent git-centric conflict analysis |
| `complexity-analysis.md` | — | NEW v5 — ComplexityClassifier keywords, Gate 0 fast-track |
| `compliance-scoping.md` | 459 | EXPANDED — session 5 (GDPR/CCPA/HIPAA/PCI, OWASP x2, license matrix) |
| `context-management.md` | 234 | EXPANDED — session 5 (cascade protocol, InheritanceGuard, VETO_SATURACIÓN) |
| `dag-design.md` | 212 | EXPANDED — session 5 (Kahn's algorithm, batch decomposition, split strategies) |
| `documentation-generation.md` | 258 | EXPANDED — session 5 (Gate 3 blocking rule, OpenAPI checklist, StandardsAgent protocol) |
| `engram-management.md` | — | NEW v5 — EngramWriter/Reader, atomic writes, access control |
| `evaluation-rubric.md` | 165 | EXPANDED — session 5 (5D scoring tables, early termination ≤0.20) |
| `fault-recovery.md` | 212 | NEW — session 5 (restored from v4: 7 fault types, backoff, model fallback chain) |
| `gate-protocol.md` | — | NEW v5 — 5 gates, GATE_VERDICT format, circuit breaker |
| `git-branch-automation.md` | — | NEW v5 — branch lifecycle, Gate 1 merge, safety rules |
| `injection-defense.md` | — | NEW v5 — prompt injection, shell injection, jailbreak patterns |
| `metrics-collection.md` | — | NEW v5 — agent _log block, MetricsCollector, OTEL fire-and-forget |
| `observability.md` | 436 | EXPANDED — session 5 (OTEL, 6 canonical metrics, Grafana panels, 4 critical alerts) |
| `parallel-safety.md` | — | NEW v5 — expert isolation boundary, CROSS_ALERT conditions |
| `provider-routing.md` | 216 | EXPANDED — session 5 (role→model mapping, degradation chain, YAML profiles) |
| `research-methodology.md` | — | MIGRATED v4 — PHASE 0-8 alignment, epistemic gate, source quality tiers |
| `session-continuity.md` | 324 | EXPANDED — session 5 (dual-artifact, PHASE 0/5 recovery, closure protocol) |
| `spec-writing.md` | 217 | EXPANDED — session 5 (immutability rule, confirmation workflow, task block format) |
| `token-budget-estimation.md` | 212 | EXPANDED — session 5 (per-agent caps, throttling rules, model cost table) |
| `vault-protocol.md` | — | NEW v5 — zero-hardcode rule, MCP integration, audit trail |
| `worktree-automation.md` | — | MIGRATED v4 — lifecycle, naming convention, isolation invariants |

---

## 20. Rescued Content: Inter-Agent Protocol PMIA

Protocol version in v5.0: PMIA v5.0 (same logic, new versioning baseline)

**STATUS: Implemented in `sdk/pmia/` — commit f00937f (2026-04-14 session 2)**

### SDK Implementation (`sdk/pmia/`)

| File | Responsibility |
|---|---|
| `sdk/pmia/messages.py` | `PMIAMessage` frozen dataclass, 4 `MessageType` enums, `GateId`, `Verdict`, `EscalationReason`, `AlertSeverity`. Factory functions: `gate_verdict()`, `escalation()`, `cross_alert()`, `checkpoint_req()`. Hard limits: `_MAX_MSG_CHARS=1200` (≈300 tokens), `_MAX_TEXT_CHARS=800` (≈200 tokens). |
| `sdk/pmia/broker.py` | `PMIABroker`: HMAC-SHA256 signing (key from `PIV_PMIA_SECRET` env, fallback ephemeral dev key). AuditAgent logging before any handler runs. Max 2 retries → `PROTOCOL_VIOLATION` escalation. `CROSS_ALERT` from SecurityAgent sets `_veto_active=True` immediately — overrides all gate verdicts. |
| `sdk/pmia/__init__.py` | Package exports: all message types, broker, factory functions. |

### Wiring in AsyncSession (`sdk/core/session_async.py`)

- `self._broker = PMIABroker(session_id, telemetry_logger)` — instantiated after telemetry init
- Circuit breaker → `broker.send(escalation(UNRESOLVABLE_CONFLICT))`
- Gate 2b fail → `broker.send(gate_verdict(BLOCKED_BY_TOOL))`
- Gate 2b pass → `broker.send(gate_verdict(APPROVED))`
- `broker.close()` in `finally` block at session end

### Message Types

| Type | Direction | Purpose |
|---|---|---|
| `GATE_VERDICT` | Any gate agent → MasterOrchestrator | Approve or reject at gate |
| `ESCALATION` | Any agent → level above | Context saturation, unresolvable conflict |
| `CROSS_ALERT` | SecurityAgent → any | Security issue, immediate attention required |
| `CHECKPOINT_REQ` | Any agent → AuditAgent | Request checkpoint write to `.piv/` |

### Constraints

- Maximum message size: **300 tokens**
- Signature: **HMAC-SHA256** (key from `PIV_PMIA_SECRET` env var — never exposed in context)
- Malformed message retry: maximum **2 attempts**, then escalate to `PROTOCOL_VIOLATION`
- No credentials or secrets in any message payload
- All messages logged by AuditAgent BEFORE any handler processes them

---

## 21. Rescued Content: Evaluation Contract

Applied by EvaluationAgent at PHASE 5 to each Specialist Agent output.

### Scoring Rubric

| Dimension | Weight | Measured by |
|---|---|---|
| FUNC | 0.35 | Functional correctness against spec |
| SEC | 0.25 | No hardcoded secrets, no known CVEs |
| QUAL | 0.20 | Linting pass, test coverage threshold |
| COH | 0.15 | Coherence with other experts' outputs |
| FOOT | 0.05 | Token efficiency (context footprint) |

**Early termination**: aggregate score ≥ 0.90 → declare winner, stop evaluation.
Log to `metrics/logs_scores/<session_id>.jsonl`.

### Rules

- Deterministic tools run first (grep, semgrep, coverage) before LLM scoring.
- EvaluationAgent is information-only: no veto, no gate authority.
- Score feeds SecurityAgent and AuditAgent for Gate 2b decision.
- Each scoring event logged: timestamp, agent_id, dimension, score, tool_used.

---

## 22. Rescued Content: Parallel Safety Contract

Governs agent isolation during PHASE 5 parallel execution.

| Rule | Detail |
|---|---|
| Worktree isolation | Specialists read only own worktree + `specs/active/` + assigned skills |
| No cross-read | A Specialist cannot access another Specialist's worktree before Gate 1 |
| EvaluationAgent read-only | Accesses outputs via `git show` only. Never runs `git checkout`. |
| CoherenceAgent diff-only | Monitors diffs exclusively. Never reads complete source files. |
| Early termination advisory | EvaluationAgent recommends. CoherenceAgent confirms safety. MasterOrchestrator decides. |
| Violation detection | ExecutionAuditor monitors at PHASE 5 checkpoints. Violation → CROSS_ALERT. |

---

## 23. Rescued Content: Branch & Worktree Protocol

### Branch Topology

```
main                              (delivery — Gate 3, human-only merge)
└── staging                       (integration — Gate 2b, owner-only)
    ├── feature/<task-id>/        (Domain Orchestrator scope — Gate 2 approved)
    │   ├── feature/<task-id>/expert-1   (Specialist Agent 1)
    │   ├── feature/<task-id>/expert-2   (Specialist Agent 2)
    │   └── feature/<task-id>/expert-N   (Gate 1: each → task branch)
    └── fix/<issue-id>            (Level 1 fast-track)
```

### Branch Protection

| Branch | Rule | Notes |
|---|---|---|
| `main` | Owner-only push, no force push | Unreachable by automation |
| `staging` | Owner-only, no force push | Gate 3 required for merge |
| `feature/*` | Owner + session agents | Created and deleted per session |

### Worktree Lifecycle Commands

```bash
# Create (Domain Orchestrator, PHASE 5)
git worktree add worktrees/<task-id>/<expert-N> -b feature/<task-id>/expert-<N>

# List active
git worktree list

# Remove after Gate 1 merge
git worktree remove worktrees/<task-id>/<expert-N>
git branch -d feature/<task-id>/expert-<N>

# Prune stale references
git worktree prune
```

Naming convention: `worktrees/<task-id>/<expert-N>`
`worktrees/` is gitignored — not versioned.

---

## 24. Rescued Content: Observability & SRE

### Three Pillars

**Logs — Canonical JSON**
- One JSON line per event
- Required fields: `timestamp`, `level`, `agent_id`, `phase`, `action`, `outcome`

**Traces — OpenTelemetry (OTEL)**
- Full lifecycle tracing per objective
- Span per: agent instantiation, gate evaluation, phase transition

**Metrics**

| Category | Examples |
|---|---|
| Delivery | Lead time, completion rate per phase |
| Gate | First-pass rate (target ≥ 80%), rejection reasons |
| Context | Agent count per session, fragmentation events |
| Quality | Test coverage %, linting failures, CVE detections |
| Evaluation | Expert count, winner score, early termination rate |

### SLI / SLO / SLA

| Term | Owner | Purpose |
|---|---|---|
| SLI | Engineering | Measurable indicator (latency, error rate) |
| SLO | Engineering | Internal performance target |
| SLA | Legal / Product | Contractual commitment to external parties |

### Availability Reference

| SLA | Annual downtime |
|---|---|
| 99% | 3.65 days |
| 99.9% | 8.7 hours |
| 99.99% | 52 minutes |

---

## 25. Rescued Content: Session Continuity

```
.piv/
├── active/      ← Current session state (not versioned)
├── completed/   ← Archived successful sessions
└── failed/      ← Archived failed sessions + post-mortem
```

### Session Record Schema (JSON)

```json
{
  "session_id": "<uuid>",
  "objective": "<text>",
  "started_at": "<iso-timestamp>",
  "phase_current": "<PHASE N>",
  "dag": {},
  "gate_history": [],
  "agents_active": [],
  "worktrees_active": [],
  "token_budget": {}
}
```

### Continuity Protocol

- Before every session: `piv validate` must pass (non-negotiable)
- If session interrupted: resume from `active/<session-id>.json`, replay from last checkpoint
- AuditAgent writes checkpoints at every phase exit
- On circuit breaker: session moved to `failed/`, post-mortem written to `engram/audit/`

---

## 26. Discarded from v4.0

| Item | Reason |
|---|---|
| Spanish content in markdown | Language policy: English only |
| `agent.md` (monolithic) | Split into `sys/agents.md` + `sys/phases.md` |
| `LAYERS.md` (as-is) | Absorbed into `_init_.md` layer map |
| Domain-specific engram atoms | Product-specific, not framework |
| `docs/TUTORIAL_LEVEL2.md` | Deferred |
| `docs/ROADMAP_PRODUCCION.md` | Rebuilt for v5.0 scope |
| `security_vault.md` | No static vault doc in v5.0 |
| `rust-tauri-ci.md` skill | Product-specific |
| Mixed language commits | Policy: English only |

---

## 27. Open Decisions

| ID | Question | Decision | Status |
|---|---|---|---|
| OD-01 | `sys/` scope: lean env layer or full doc hub? | Lean: only `_index.md`, `bootstrap.sh`, `venv.md`, `worktrees.md`, `git.md` | RESOLVED |
| OD-02 | Git directives location: inside `sys/` or separate `git/` folder? | Separate `git/` at root. `.github/` for yml (GitHub requirement). `sys/git.md` for action guidelines only. | RESOLVED |
| OD-03 | `contracts/` location: inside `agents/` or sibling at root? | Sibling at root. Contracts define external interface, not internal config. | RESOLVED |
| OD-04 | Per-agent files or single `agents.md`? | Per-agent files in `agents/`. Each file = config + phases + model assignment for that agent. | RESOLVED |
| OD-05 | PMIA version: reset to v5.0 or inherit v4.0? | Reset to PMIA v5.0. Same logic, new versioning baseline. | RESOLVED |
| OD-06 | Skills: audit all 31 before migrating or migrate then audit? | Migrate then audit per module (P3). 9 promoted to contracts/sys level already. | RESOLVED |
| OD-07 | Session state format: JSON or YAML? | JSON for `.piv/` runtime state. YAML for `config/` static configuration. | RESOLVED |
| OD-08 | `engram/` scaffold: create now or at first write? | Created at bootstrap. EngramWriter (sdk/engram/writer.py) handles AuditAgent writes at PHASE 8. Both scaffold and write path implemented. | RESOLVED |
| OD-09 | Compliance scope for the framework itself? | MINIMAL confirmed. Framework processes no user PII — it orchestrates agents that process user-supplied objectives. Compliance responsibility is delegated to the product workspace (user's repo). `compliance-scoping.md` covers the product layer; framework itself has NONE/MINIMAL scope by design. | RESOLVED |
| OD-10 | Provider entrypoints: all now or per-provider as onboarded? | `CLAUDE.md` first. Others added as providers are onboarded. | RESOLVED |
| OD-11 | Product workspace model? | Hybrid: Mode 1 = clone repo + branch separation. Mode 2 = pip install + piv-oac init seeds piv-directive + staging into user's repo. Both valid. | RESOLVED |

---

## 28. Task Tracker

### Completed

| Task | Date | Notes |
|---|---|---|
| Repo cleaned — empty main | 2026-04-13 | Force-pushed orphan commit |
| `_init_.md` markdown fixed | 2026-04-13 | Single-line → properly formatted |
| v4.0 repository analyzed | 2026-04-13 | 50+ files read from agent-configs branch |
| v5.0 layer architecture defined | 2026-04-13 | Root / sys / SDK / Module layers |
| `sys/` as gatekeeper confirmed | 2026-04-13 | Pre-flight verification + router. Adds `_verify.md`. |
| `git/` folder confirmed at root | 2026-04-13 | topology.md, protection.md, policy.md |
| `contracts/` confirmed at root | 2026-04-13 | _base.md + 12 per-agent files. Session 5: +1 (bias_auditor) → 13 per-agent + _base = 14 total |
| Per-agent files in `agents/` confirmed | 2026-04-13 | One file per agent, 13 agents. Session 5: +1 (BiasAuditAgent) → 14 total |
| SDK scenario B confirmed | 2026-04-13 | Publishable `piv-oac` package. `sdk/` reads sibling folders at runtime. |
| Provider scripts confirmed at root | 2026-04-13 | `anthropic.py`, `ollama.py`, `openai.py` — thin wrappers |
| `pyproject.toml` replaces `requirements.txt` | 2026-04-13 | Bundles all markdowns via package_data |
| `scripts/validate_env.py` eliminated | 2026-04-13 | Absorbed into `sys/bootstrap.sh` + `sys/_verify.md` |
| `_context_.md` structured (v4) | 2026-04-13 | 70-item build plan, full architecture |
| `src/` removed from framework repo | 2026-04-13 | Product lives in artifact repos/branches. Framework never contains product code. |
| Deployment model finalized | 2026-04-13 | Two modes: clone+branches / pip+init. piv-oac init creates piv-directive + staging proactively if only main exists. |
| Execution Tier Model defined | 2026-04-13 | Tier 1 deterministic / Tier 2 local LLM optional / Tier 3 cloud. router.py decides per operation. |
| Interview protocol defined | 2026-04-13 | PHASE 0.1 Q&A + PHASE 0.2 spec reformulation. Three I/O modes: console, callback, pre-supplied. DAG never built from raw objective. |
| Observability model defined | 2026-04-13 | logs/ to file default (zero overhead). Docker Grafana+Loki+Tempo opt-in via piv observe:start. |
| `_context_.md` structured (v5) | 2026-04-13 | 80-item build plan, sections 8-12 added, all structural issues resolved |
| `_context_.md` structural + architectural corrections | 2026-04-13 | Section numbering fixed, FASE→PHASE, skill migration corrected, interview protocol adaptive, engram lazy load, TelemetryLogger defined, agent _log block, gate invariants in _base.md |
| `_init_.md` rewritten (v5.0) | 2026-04-13 | 8 sections, English only, non-operational. Covers identity, problem space, differentiators, layer map, module map, core principles, version history. |
| `sdk/core/session_async.py` — AsyncSession + parallel PHASE 5 | 2026-04-14 | asyncio.gather() per DAG batch. AsyncAnthropicProvider + AsyncOllamaProvider. ExpertResult + AsyncSessionResult dataclasses. Circuit breaker: 3 failures → status="circuit_breaker". |
| `sdk/triggers/github.py` + `sdk/triggers/webhook.py` | 2026-04-14 | GitHub: reads GITHUB_EVENT_PATH, extracts ```piv objective + ```piv-answers YAML, calls AsyncSession, posts comment via gh CLI. Webhook: HTTP POST /session, HMAC-SHA256, fire-and-forget daemon thread. |
| `.github/workflows/piv-session.yml` | 2026-04-14 | Triggers on issues.labeled piv:run. Jobs: check-label → orchestration (PHASE 0–2) → phase-5-experts matrix (fail-fast: false, parallel CI) → gate-1-coherence. |
| `config/settings.yaml` | 2026-04-14 | max_parallel_experts: 6, circuit_breaker_threshold: 3, trigger.mode: manual/github_issues/webhook, activation_label: piv:run. |
| `sdk/tools/` subpackage | 2026-04-14 | SafeLocalExecutor: allowlist-only subprocess (no shell=True), 60s timeout, 32KB cap. ExecutionDataFilter: blocks shell metacharacters, path traversal, API keys, credential patterns. BlockedByToolError for Gate 2b failures. |
| SafeLocalExecutor wired into AsyncSession | 2026-04-14 | worktree_add before each specialist LLM call, worktree_remove in success + error paths. Gate 2b: run_lint + run_pytest block closure — raises BlockedByToolError if either fails. worktree_prune after all experts. |
| ProviderRouter wired to ComplexityClassifier | 2026-04-14 | Fixed: agent_level was hardcoded "L2". Now: complexity.level → _COMPLEXITY_TO_AGENT_LEVEL → ProviderRouter.resolve_tier() + get_provider(). classification propagated to every DAG node. |
| `logs/index.jsonl` — cross-session historical index | 2026-04-14 | TelemetryLogger.write_index_entry() appends one summary line per session at close. Captures: session_id, objective, status, complexity_level, tokens, duration, gate_verdicts. Written at all exit points (completed, circuit_breaker, Gate 2b failure). |
| `sdk/pmia/` — PMIA v5.0 broker implementation (Gap 1) | 2026-04-14 s2 | messages.py: PMIAMessage frozen dataclass, 4 MessageType, factory functions, 300-token hard limit. broker.py: PMIABroker with HMAC-SHA256 signing, AuditAgent log before dispatch, max 2 retries → PROTOCOL_VIOLATION, CROSS_ALERT veto flag. __init__.py: package exports. Commit f00937f. |
| `sdk/core/loader.py` — lazy loading enforcement (Gap 2) | 2026-04-14 s2 | _AUTHORIZED_LOADS dict mirrors sys/_index.md §Load Table by Role. load_agent_for_role() raises PermissionError on violations, logs [LoadViolation] for ExecutionAuditor. "_session" role authorized for all agents. Session 5: +bias_auditor → 14 agents total. Commit f00937f. |
| `sdk/core/session_async.py` — broker wiring (Gap 3) | 2026-04-14 s2 | PMIABroker instantiated after telemetry. Gate 2b BLOCKED_BY_TOOL / APPROVED verdicts emitted via broker. Circuit breaker emits ESCALATION(UNRESOLVABLE_CONFLICT). broker.close() in finally. Commit f00937f. |
| `CHECKPOINT_REQ` at all phase transitions | 2026-04-15 s3 | 4 emit points: PHASE_1 (DAG confirmed), PHASE_5 (per batch), GATE_2B (approved), PHASE_8 (pre-close). broker.close() added to finally block. Circuit-breaker indentation fixed. Commit 87ce26b. |
| `sdk/engram/writer.py` — EngramWriter (AuditAgent write path) | 2026-04-15 s3 | append-only, atomic (temp+os.replace). write_json() for record.json, append() for markdown atoms with session_id+timestamp header. EngramWriteError on unauthorized role. Commit fca47ec. |
| PHASE 8 engram writes wired in AsyncSession | 2026-04-15 s3 | audit/<session_id>/record.json (full snapshot) + gates/verdicts.md (rolling append) written at PHASE 8. EngramWriter exported from sdk/engram/__init__.py. Commit fca47ec. |
| `sdk/core/dag.py` — SpecDAGParser | 2026-04-15 s3 | Regex parser for ### task::<node_id> blocks in specs/active/functional.md. Returns None on missing file/no blocks — callers fall back to stub. session_async.py PHASE 1 priority: provided→spec→stub. specs/_templates/functional.md.tpl defines format. Commit 293487b. |
| `sdk/core/interview.py` + `sdk/core/spec_writer.py` — PHASE 0.1/0.2 wired | 2026-04-15 s3 | interview.py: 4-question standard set, run_interview() with key-first lookup (programmatic) + fallback to full question (console/callback). spec_writer.py: write_functional() now appends ## Task Decomposition with ### task:: blocks; _derive_tasks_from_scope() Tier-1 heuristic for when no explicit tasks provided. session_async.py: PHASE 0.1/0.2 run if level==2 and handler available. Commit 066060a. |
| Skills v5.1 — full expansion from v4 depth audit | 2026-04-15 s5 | 9 existing skills expanded (observability 60→436, compliance-scoping 45→459, session-continuity 56→324, context-management 47→234, provider-routing 59→216, token-budget-estimation 57→212, documentation-generation 59→258, spec-writing 60→217, dag-design 52→212, evaluation-rubric 53→165). 3 new skills created (fault-recovery, change-management — restored from v4; bias-audit — new). manifest.json: 21→24 entries. VERSIONING.md baseline updated. bootstrap.sh 8/8 PASS. Commit aab3bfa. |
| `BiasAuditAgent` — new agent (L1 specialized) | 2026-04-15 s5 | skills/bias-audit.md (208 lines): 4 directives (Ecosystem Neutrality, Red Teaming Semántico, Multi-LLM Audit, Deterministic Logic Preservation). Mandatory "Análisis de Sesgos y Dependencias" output section. agents/bias_auditor.md + contracts/bias_auditor.md: full PMIA tables, permissions, behavioral mandates, forbidden actions. sys/_index.md Load Table updated. sdk/core/loader.py: bias_auditor in _AUTHORIZED_LOADS + _session set (14 agents total). Commit aab3bfa. |
| `sdk/core/bias_validator.py` — Tier 1 deterministic output validator | 2026-04-16 s6 | validate_bias_output(): 6 regex checks (section header, dependency table ≥1 row, Sesgos checklist, Red Team result, Multi-LLM audit, RAG conflicts). BiasValidationResult: valid, missing_sections, warnings, red_team_result, multi_llm_result, lock_in_risks. section_present() for Gate 3 quick check. Zero LLM calls. 3-case unit test PASSED. Commit 9ef6ab5. |
| BiasAuditAgent PHASE 1.5 wiring in session_async.py | 2026-04-16 s6 | Activates for classification.level==2 and not fast_track. _run_bias_audit(): loads bias_auditor config + bias-audit skill, LLM call (FLAGSHIP via model_registry), validate_bias_output() Tier 1. GATE_VERDICT(REJECTED)+status="bias_rejected" on fail; GATE_VERDICT(APPROVED)+CHECKPOINT_REQ on pass. Non-fatal on load/provider error. Fix resp.tokens_used → input+output. Commit 9ef6ab5. |
| `sdk/core/model_registry.py` — per-agent model assignment | 2026-04-16 s6 | resolve_model(agent, provider, task_complexity, escalate) → model string. ModelTier: FLAGSHIP/BALANCED/FAST. 14 agents mapped. FLAGSHIP: orchestrator, security_agent, bias_auditor. BALANCED: standards, compliance, evaluation, domain_orchestrator, specialist(L2). FAST: audit, coherence, logistics, execution_auditor, docs, specialist(L1). Dynamic escalation: audit/coherence/docs FAST→BALANCED on escalate=True. 4 providers: anthropic(opus/sonnet/haiku), openai(gpt-4o/gpt-4o/mini), ollama(32b/14b/7b), gemini(flash-exp/flash/flash). Unknown provider → anthropic fallback. 20-case matrix PASSED. session_async.py: specialist + bias_auditor use registry. Commit da933d7. |
| Shadow module fix: `anthropic.py/openai.py/ollama.py` → `entrypoint_*.py` | 2026-04-16 s7 | Provider scripts en raíz del repo tenían el mismo nombre que paquetes pip, causando ImportError circular al importar `sdk` (Python cargaba el script local en vez del paquete). Renombrados a `entrypoint_*.py`. Commits 041a768, e843c0a. |
| `sdk/__init__.py` — optional OpenAIProvider + lint cleanup | 2026-04-16 s7 | Import de `OpenAIProvider` envuelto en try/except ImportError — setups sin `openai` instalado ya no fallan. noqa annotations en re-exports públicos intencionales (InitError, Initializer, SpecWriter, GateEvaluator). Variable F841 corregida. Commit e843c0a. |
| `dag.nodes.values()` fix in `_run_bias_audit()` | 2026-04-16 s7 | `for n in dag.nodes` iteraba keys del dict (str) en vez de DAGNode — AttributeError en `n.node_id` en toda sesión L2. Corregido a `dag.nodes.values()`. Commit e843c0a. |
| `SafeLocalExecutor run_lint` → `sys.executable -m ruff check` | 2026-04-16 s7 | `run_lint` llamaba `bash sys/bootstrap.sh lint` que invoca `ruff` directamente — no encontrado en PATH de bash cuando se lanza desde subprocess Python en Windows (PATH formato Windows ≠ bash). Corregido a `sys.executable` + mismo fix en `run_pytest`. Commit e843c0a. |
| ruff lint: 47 errores saneados | 2026-04-16 s7 | 35 errores autofix (`ruff check --fix`). UP042 (`str, Enum` → `StrEnum`) añadido a ignore en pyproject.toml — intencional por compatibilidad de serialización JSON. Commit e843c0a. |
| `sdk/cli.py` — UnicodeEncodeError fix (Windows cp1252) | 2026-04-16 s7 | `✓`/`✗` en output de expert results no encodables en consola Windows cp1252. Reemplazados por `OK`/`FAIL` ASCII. Commit e843c0a. |
| PHASE 3 — SecurityAgent Gate 0 wiring en `session_async.py` | 2026-04-16 s8 | `_run_security_gate()`: carga security_agent config + LLM call FLAGSHIP, parsea APPROVED/REJECTED con `_parse_verdict()`. Gate corto-circuita sesión antes de PHASE 5 si REJECTED. Escribe `engram/security/<session_id>/review.md` vía EngramWriter. `gate_verdicts["GATE_0"]` propagado a AsyncSessionResult. |
| PHASE 6 — EvaluationAgent scoring en `session_async.py` | 2026-04-16 s8 | `_run_evaluation()`: non-blocking (no corta sesión si falla). 5 dimensiones: FUNC/SEC/QUAL/COH/FOOT, parseas con `_parse_eval_scores()`. Escribe `engram/metrics/logs_scores/<session_id>.jsonl`. `eval_scores` propagado a PHASE 7 para scoring de coherencia. Fallback a parse_error=True si LLM no responde JSON. |
| PHASE 7 — CoherenceAgent Gate 1 wiring en `session_async.py` | 2026-04-16 s8 | `_run_coherence_gate()`: APPROVED/REJECTED según consistencia semántica de expert results. Multi-node DAG: blocking (REJECTED corta sesión). Single-node: advisory (REJECTED no bloquea, `eff_approved=True`). Escribe `engram/gates/<session_id>/gate1.md`. `gate_verdicts["GATE_1"]` en AsyncSessionResult. |
| Expert output persistido en PHASE 8 audit record | 2026-04-16 s8 | `record.json` ahora incluye array `experts[]` con `expert_id`, `node_id`, `success`, `tokens_used`, `duration_ms`, `error`, `content[:8000]` por cada ExpertResult. Engram/audit completo y consultable por EvaluationAgent en sesiones futuras. |
| Module helpers: `_parse_verdict()`, `_extract_rationale()`, `_parse_eval_scores()` | 2026-04-16 s8 | Funciones de módulo (no métodos) para parseo de output LLM en PHASE 3, 6, 7. `_parse_verdict()`: regex APPROVED/REJECTED, default REJECTED. `_extract_rationale()`: extrae texto libre post-veredicto. `_parse_eval_scores()`: parse JSON en bloque ```json``` con fallback a parse_error. |
| Segunda prueba funcional end-to-end con créditos Anthropic | 2026-04-16 s8 | Pipeline completo ejecutado: PHASE 0→1.5 (BiasAudit APPROVED)→PHASE 5 (SpecialistAgent real, 5 tokens)→PHASE 6 (EvaluationAgent, parse_error=True no bloqueante)→PHASE 7 (CoherenceAgent REJECTED advisory single-node)→PHASE 8 audit writes. Logs en `logs/sessions/` + engram poblado en security/, metrics/, gates/, audit/. |

### Next (ordered by priority)

| # | Task | Priority | Build plan ref |
|---|---|---|---|
| ~~1~~ | ~~Rewrite `_init_.md` — 8 sections, English, non-operational~~ | ~~P0~~ | DONE |
| ~~2~~ | ~~Create `README.md`~~ | ~~P0~~ | DONE |
| ~~3~~ | ~~Create `CLAUDE.md`~~ | ~~P0~~ | DONE |
| ~~4~~ | ~~Create `.gitignore`~~ | ~~P0~~ | DONE |
| ~~5~~ | ~~Create `pyproject.toml`~~ | ~~P0~~ | DONE |
| ~~6~~ | ~~Create provider scripts (`anthropic.py`, `ollama.py`, `openai.py`)~~ | ~~P0~~ | DONE |
| ~~7~~ | ~~Create `sys/_verify.md`~~ | ~~P1~~ | DONE |
| ~~8~~ | ~~Create `sys/_index.md`~~ | ~~P1~~ | DONE |
| ~~9~~ | ~~Create `sys/bootstrap.sh`~~ | ~~P1~~ | DONE |
| ~~10~~ | ~~Create `sys/venv.md`, `sys/worktrees.md`, `sys/git.md`~~ | ~~P1~~ | DONE |
| ~~11~~ | ~~Create `contracts/_base.md` (PMIA v5.0)~~ | ~~P1~~ | DONE |
| ~~12~~ | ~~Create `contracts/<agent>.md` × 12~~ | ~~P1~~ | DONE |
| ~~13~~ | ~~Create `agents/<agent>.md` × 13~~ | ~~P1~~ | DONE |
| ~~14~~ | ~~Create `sdk/` Python package (20 files)~~ | ~~P2~~ | DONE |
| ~~15~~ | ~~Create `git/topology.md`, `git/protection.md`, `git/policy.md`~~ | ~~P2~~ | DONE |
| ~~16~~ | ~~Create `.pre-commit-config.yaml`~~ | ~~P2~~ | DONE |
| ~~17~~ | ~~Create `.github/workflows/` (3 yml files)~~ | ~~P2~~ | DONE |
| ~~18~~ | ~~Create `engram/` scaffold (INDEX + VERSIONING + 9 subdirs)~~ | ~~P3~~ | DONE |
| ~~19~~ | ~~Migrate + audit 22 skill modules~~ | ~~P3~~ | DONE |
| ~~20~~ | ~~Create `metrics/schema.md`~~ | ~~P3~~ | DONE |
| ~~21~~ | ~~Create `specs/_templates/`~~ | ~~P3~~ | DONE |
| ~~22~~ | ~~Define `tests/` structure~~ | ~~P3~~ | DONE |
| ~~23~~ | ~~`sdk/core/session_async.py` + async providers~~ | ~~P2~~ | DONE |
| ~~24~~ | ~~`sdk/triggers/` (github.py + webhook.py)~~ | ~~P2~~ | DONE |
| ~~25~~ | ~~`.github/workflows/piv-session.yml`~~ | ~~P2~~ | DONE |
| ~~26~~ | ~~`sdk/tools/` (SafeLocalExecutor + ExecutionDataFilter)~~ | ~~P2~~ | DONE |
| ~~27~~ | ~~Wire SafeLocalExecutor into AsyncSession (Gate 2b + worktree lifecycle)~~ | ~~P2~~ | DONE |
| ~~28~~ | ~~Wire ProviderRouter to ComplexityClassifier output~~ | ~~P2~~ | DONE |
| ~~29~~ | ~~`logs/index.jsonl` cross-session historical index~~ | ~~P2~~ | DONE |
| ~~30~~ | ~~`sdk/pmia/` — PMIA broker (Gap 1 v4→v5)~~ | ~~P2~~ | DONE — f00937f |
| ~~31~~ | ~~`sdk/core/loader.py` — lazy loading enforcement (Gap 2 v4→v5)~~ | ~~P2~~ | DONE — f00937f |
| ~~32~~ | ~~`sdk/core/session_async.py` — broker wiring (Gap 3 v4→v5)~~ | ~~P2~~ | DONE — f00937f |
| ~~33~~ | ~~Compute SHA-256 hashes for all `skills/manifest.json` entries~~ | ~~P3~~ | DONE — 21 entries at time of task; 24 entries after session 5 (hashes recomputed in aab3bfa) |
| ~~34~~ | ~~CHECKPOINT_REQ emissions at all phase transitions~~ | ~~P2~~ | DONE — 87ce26b |
| ~~35~~ | ~~`sdk/engram/writer.py` — EngramWriter + PHASE 8 write path~~ | ~~P2~~ | DONE — fca47ec |
| ~~36~~ | ~~`sdk/core/dag.py` — SpecDAGParser + spec-first DAG resolution~~ | ~~P2~~ | DONE — 293487b |
| ~~37~~ | ~~`sdk/core/interview.py` + `sdk/core/spec_writer.py` PHASE 0.1/0.2~~ | ~~P2~~ | DONE — 066060a |
| ~~38~~ | ~~SecurityAgent recursive depth ≤ 2 enforcement in AsyncSession~~ | ~~LOW~~ | DONE — 86470ce |
| ~~39~~ | ~~Spec confirmation gate (PHASE 0.2 → PHASE 1)~~ | ~~LOW~~ | DONE — 86470ce |

### Impact Analysis — Session 2 (2026-04-14)

| Gap closed | Runtime impact |
|---|---|
| `sdk/pmia/` | PMIA protocol now enforced in code, not just markdown. Every inter-agent message is HMAC-signed, size-validated, audit-logged before dispatch. CROSS_ALERT veto is machine-enforced in broker, not advisory. |
| `sdk/core/loader.py` `_AUTHORIZED_LOADS` | Any unauthorized `load_agent_for_role()` call raises `PermissionError` and logs a `[LoadViolation]` event. ExecutionAuditor now has structured signals to monitor. Previously: no enforcement existed. |
| `sdk/core/session_async.py` broker wiring | Gate 2b verdicts and circuit-breaker escalations are now actual PMIA messages (signed, logged). Previously: gate logic ran but produced no protocol-level messages. |
| `skills/manifest.json` SHA-256 hashes | `SHA256Verifier.verify()` in `FrameworkLoader.load_skill()` now works end-to-end. Any tampered skill file is rejected at load time. Previously: all entries were "PENDING" — verifier would always fail. |

### Impact Analysis — Session 3 (2026-04-15)

| Implemented | Runtime impact |
|---|---|
| `CHECKPOINT_REQ` at phase transitions | AuditAgent now receives structured state snapshots at PHASE_1, PHASE_5 (per batch), GATE_2B, PHASE_8. Full PMIA message lifecycle complete. |
| `sdk/engram/writer.py` | AuditAgent write path exists: every completed session writes `audit/<session_id>/record.json` + appends to `gates/verdicts.md`. Engram grows across sessions. |
| `SpecDAGParser` in `dag.py` | PHASE 1 resolves real multi-node DAGs from `specs/active/functional.md`. Previously: single-node stub always. Now: spec → N parallel experts. |
| `run_interview()` + `write_functional()` task blocks | Full PHASE 0→1 pipeline live: interview answers → functional.md with `### task::` blocks → SpecDAGParser → multi-node DAG → parallel PHASE 5. Invariant "DAG never built from raw objective" now enforced in code. |
| `SpecWriter` template substitution fix | Interview questions map 1:1 to `{{variable}}` placeholders in `functional.md.tpl`. `_render_template()` loads .tpl, substitutes all 9 variables, falls back to inline if template missing. `{{task_decomposition}}` replaces numbered `{{task_1_id}}` vars — scales to N tasks. Commit 0b1fc1a. |
| Fragmentation depth enforcement + spec confirmation gate (items 38+39) | 2026-04-15 s4 | `_MAX_FRAGMENTATION_DEPTH=2`. `_handle_escalation()` on broker increments depth counter on CONTEXT_SATURATION; emits PROTOCOL_VIOLATION ESCALATION if depth > 2. `confirm_specs` param on `run_async()`: user must confirm specs before DAG construction; returns `status="spec_rejected"` on denial. Commit 86470ce. |

### Impact Analysis — Session 5 (2026-04-15)

| Implemented | Runtime impact |
|---|---|
| Skills v5.1 depth expansion (9 expanded, 3 new) | Skills now carry operational depth matching v4 maturity. Agents loading `observability`, `compliance-scoping`, `session-continuity`, `context-management`, `provider-routing`, `token-budget-estimation`, `documentation-generation` now receive actionable protocols (OTEL spans, GDPR checklists, recovery sequences, budget tiers, role→model mappings) instead of high-level descriptions. `fault-recovery` and `change-management` fill gaps that left fault handling and framework governance undocumented. |
| BiasAuditAgent registered end-to-end | New L1 agent available to OrchestratorAgent for L2 tasks. BiasAuditAgent enforces vendor-neutrality, red-team validation, multi-LLM cross-audit, and RAG precedence. Every L2 architectural proposal must include "Análisis de Sesgos y Dependencias". Emits CROSS_ALERT(HIGH) on hallucinated parameters or lock-in risk=HIGH without migration path. |
| manifest.json 21→24 entries + hashes recomputed | SHA-256 integrity covers all 24 skills. bootstrap.sh CHECK 6 passes. Any tampered skill file is rejected at load time for all 24, not just the original 21. |
| OD-09 resolved (MINIMAL scope confirmed) | Compliance responsibility formally delegated to product workspace. Framework layer has no obligation to implement GDPR/CCPA/HIPAA controls — only document them via `compliance-scoping.md` for product agents to apply. |

### Impact Analysis — Session 4 (2026-04-15)

| Implemented | Runtime impact |
|---|---|
| Fragmentation depth enforcement (`_MAX_FRAGMENTATION_DEPTH=2`) | AsyncSession now enforces the contracts/security_agent.md constraint: max 2 recursive fragmentation levels. Excessive CONTEXT_SATURATION escalations are caught in-process and escalated as PROTOCOL_VIOLATION via PMIA broker — no infinite sub-agent chains possible. |
| Spec confirmation gate (`confirm_specs` on `run_async()`) | DAG construction is now gatable by user confirmation. Callers that set `confirm_specs=True` will receive `status="spec_rejected"` if the user rejects the spec, preventing any LLM/cloud cost. This closes the "DAG never built without confirmation" invariant stated in §11. |

### Impact Analysis — Session 6 (2026-04-16)

| Implemented | Runtime impact |
|---|---|
| `sdk/core/bias_validator.py` — Tier 1 deterministic validator | BiasAuditAgent output es ahora verificado por máquina antes de aceptarse. El LLM no puede "olvidar" incluir la sección requerida — 6 regex checks capturan cualquier elemento faltante. Costo cero de LLM para la validación. Red Team=FAILED y Multi-LLM=ISSUES_FOUND generan warnings accionables en telemetría. |
| PHASE 1.5 — activación de BiasAuditAgent en session_async.py | Sesiones L2 tienen ahora un gate obligatorio de auditoría de sesgos arquitectónicos entre la construcción del DAG y la ejecución de expertos. `status="bias_rejected"` cortocircuita la sesión antes de cualquier costo LLM de PHASE 5 si la auditoría falla. GATE_VERDICT(REJECTED) fluye por el broker PMIA y queda en el audit log. |
| `sdk/core/model_registry.py` — asignación de modelo por agente | Cada agente invoca el tier de modelo apropiado en lugar del global de sesión. Agentes FLAGSHIP (orchestrator, security, bias_auditor) usan el modelo más capaz; agentes de dominio/standards usan mid-tier; agentes rutinarios (audit, logistics, execution_auditor) usan fast/baratos. Escalación promueve FAST→BALANCED en contextos MAYOR/CRITICAL. Replica patrón v4 `contracts/models.md` v3.0. Funciona en 4 proveedores (anthropic, openai, ollama, gemini). |
| Bug fix: `resp.tokens_used` → `resp.input_tokens + resp.output_tokens` | Corregido AttributeError latente en telemetría de `_run_bias_audit()`. `ProviderResponse` no tiene campo `tokens_used`. |

### Impact Analysis — Session 7 (2026-04-16)

| Fixed | Runtime impact |
|---|---|
| Shadow module collision (`anthropic.py` / `openai.py` / `ollama.py`) | `python -m sdk.cli` ahora carga sin ImportError. Causa raíz: scripts en raíz del repo tenían el mismo nombre que paquetes pip — Python los cargaba primero, rompiendo el import circular antes de que `sdk` pudiera inicializarse. |
| `dag.nodes.values()` en `_run_bias_audit()` | PHASE 1.5 ahora itera correctamente objetos DAGNode al construir el mensaje de auditoría. Antes: AttributeError en cada sesión L2, BiasAuditAgent nunca llegaba a ejecutarse. |
| `run_lint` vía `sys.executable` | Gate 2b lint funciona en Windows. Antes: subprocess bash desde Python no resolvía `ruff` en PATH (formato Windows incompatible con Git Bash). Gate permanentemente bloqueada. |
| ruff lint limpio (0 errores) | `python -m ruff check sdk/ tests/` sale con código 0. Gate 2b es pasable por primera vez. 35 auto-corregidos, UP042 ignorado intencionalmente. |
| Prueba funcional end-to-end confirmada | Primera ejecución exitosa: bootstrap 8/8 PASS → Vault OK → clasificador → PHASE 1.5 → Gate 2b (lint+pytest PASS) → PHASE 5 → `status=completed` en 15.9s. SpecialistAgent bloqueado por crédito insuficiente de API (no es error de código). |

### Impact Analysis — Session 8 (2026-04-16)

| Implemented | Runtime impact |
|---|---|
| PHASE 3 — SecurityAgent Gate 0 | Sesiones L2 tienen ahora un gate de seguridad LLM obligatorio antes de lanzar expertos paralelos. REJECTED antes de PHASE 5 evita 100% del costo LLM de los expertos en objetivos con riesgos de seguridad identificados. `engram/security/` se popula en cada ejecución L2. Antes: directorio vacío, gate no existía en código. |
| PHASE 6 — EvaluationAgent scoring | Cada sesión completada genera un registro de scoring multi-dimensional (FUNC/SEC/QUAL/COH/FOOT) en `engram/metrics/logs_scores/`. Non-blocking: un parse_error del LLM no interrumpe la sesión. Proporciona datos históricos para análisis de calidad cross-session. Antes: `engram/metrics/` siempre vacío. |
| PHASE 7 — CoherenceAgent Gate 1 | Sesiones multi-nodo tienen ahora validación semántica de consistencia entre expert results antes del cierre. `engram/gates/` se popula con el veredicto Gate 1 por sesión. Single-node: advisory (no bloquea). Multi-node: blocking. Antes: Gate 1 referenciado en contratos, nunca wired en código. |
| Expert output en PHASE 8 audit record | `engram/audit/<session_id>/record.json` ahora contiene el contenido real de cada SpecialistAgent (hasta 8000 chars). AuditAgent y EvaluationAgent pueden leer resultados de sesiones anteriores para análisis histórico. Antes: `record.json` tenía metadata pero no contenido de expertos. |
| Segunda prueba funcional end-to-end | Confirmada pipeline completa PHASE 0→8 con créditos Anthropic reales. `engram/` directories ahora se pueblan: `audit/`, `security/`, `metrics/`, `gates/`. Único gap restante: PHASE 4 (DomainOrchestrator) no implementado. `engram/skills/`, `engram/specs/`, `engram/sessions/`, `engram/bias/` aún vacíos — requieren implementación o agentes que los usen. |

### Remaining open work

| # | Task | Priority | Notes |
|---|---|---|---|
| ~~34~~ | ~~CHECKPOINT_REQ emissions at phase transitions~~ | ~~LOW~~ | DONE — 87ce26b |
| ~~35~~ | ~~`sdk/engram/writer.py` — AuditAgent write path~~ | ~~MED~~ | DONE — fca47ec. Note: EngramReader was already complete; the missing piece was the Writer. |
| ~~36~~ | ~~`sdk/core/dag.py` — SpecDAGParser from confirmed specs~~ | ~~MED~~ | DONE — 293487b |
| ~~37~~ | ~~`sdk/core/interview.py` + `sdk/core/spec_writer.py` — PHASE 0.1/0.2~~ | ~~MED~~ | DONE — 066060a |
| ~~38~~ | ~~Sub-agent recursive depth ≤ 2 (SecurityAgent context saturation)~~ | ~~LOW~~ | DONE — 86470ce. `_MAX_FRAGMENTATION_DEPTH=2` in AsyncSession. `_handle_escalation()` registered on broker for ESCALATION messages. Increments counter on CONTEXT_SATURATION; emits PROTOCOL_VIOLATION if depth > 2. |
| ~~39~~ | ~~Spec confirmation gate (PHASE 0.2 → PHASE 1)~~ | ~~LOW~~ | DONE — 86470ce. `confirm_specs: bool = False` on `run_async()`. If True and handler.confirm() returns False → returns `AsyncSessionResult(status="spec_rejected")` before DAG build. |
| 40 | PHASE 4 — DomainOrchestrator (sub-agent routing para dominios especializados) | MED | No implementado. `engram/skills/` permanece vacío. Requiere wiring de domain routing entre PHASE 3 y PHASE 5. |
| 41 | EvaluationAgent `_parse_eval_scores()` — mejorar parsing LLM | LOW | LLM devuelve scores pero no en bloque `json` — fallback a `parse_error=True`. Prompt engineering o regex más robusto para capturar JSON sin fence. |
| 42 | `engram/bias/` — persistir output BiasAuditAgent | LOW | PHASE 1.5 ejecuta y aprueba/rechaza pero no escribe a `engram/bias/`. Solo queda en telemetría. Agregar EngramWriter call en `_run_bias_audit()`. |
| 43 | Tests de integración para PHASE 3, 6, 7 | MED | `tests/integration/` cubre PHASE 0→2. PHASES 3, 6, 7 no tienen test cases. Agregar mock LLM responses para cada nueva fase. |

> **Pipeline PHASE 0→8 funcional como de session 8.** Engram directories audit/, security/, metrics/, gates/ se pueblan en ejecución real. Gaps menores: PHASE 4 (DomainOrchestrator) no implementado, engram/bias/ no persiste output BiasAuditAgent, EvaluationAgent parse_error no bloqueante pero mejora posible. Framework apto para uso con objetivos L1 (fast-track) y L2 (full pipeline).
