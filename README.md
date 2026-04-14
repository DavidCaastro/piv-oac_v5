# PIV/OAC v5.0

**Paradigm of Verifiable Intentionality / Atomic Context Orchestration**

A framework for AI-guided software development that enforces verifiable intent and atomic
context orchestration as non-negotiable operating conditions. Agents operate under
deterministic governance rules — gates that block, contracts that constrain, and audit
trails that persist across sessions. No agent executes without a confirmed specification.
No credential appears in context. No merge reaches `main` without human confirmation.

---

## Quick start

```bash
# Mode 1 — clone and work directly
git clone <repo-url>
cd piv-oac_v5
bash sys/bootstrap.sh setup     # venv + pip install + piv validate

# Mode 2 — embed in an existing project
pip install piv-oac
piv-oac init --provider=anthropic
```

For full setup, verification steps, and environment requirements: see [`sys/_verify.md`](sys/_verify.md).

---

## Where to start reading

| You are | Start here |
|---|---|
| New to PIV/OAC | [`_init_.md`](_init_.md) — what it is and why |
| Building or modifying the framework | [`_context_.md`](_context_.md) — decisions, build plan, task tracker |
| An agent starting a session | [`sys/_index.md`](sys/_index.md) — verification and routing |
| Looking for a specific module | [`sys/_index.md`](sys/_index.md) — load order by role and task |

---

## Repository structure

```
piv-oac_v5/
├── _init_.md          ← framework identity and principles (non-operational)
├── _context_.md       ← build context, decisions, task tracker
├── README.md          ← this file
├── CLAUDE.md          ← Anthropic Claude Code entrypoint
├── pyproject.toml     ← Python package definition (piv-oac on PyPI)
├── .gitignore
│
├── sys/               ← gatekeeper: pre-flight verification + agent routing
├── sdk/               ← Python engine (publishable package)
├── agents/            ← per-agent configuration (13 agents)
├── contracts/         ← PMIA v5.0 inter-agent communication standard
├── skills/            ← lazy-loaded knowledge modules (21 files + manifest)
├── engram/            ← cross-session persistent memory
├── git/               ← branch topology, protection rules, commit policy
├── specs/             ← specification templates and active specs
├── metrics/           ← session evaluation schema and scores
├── observability/     ← optional Docker stack (Grafana + Loki + Tempo)
├── config/            ← runtime YAML configuration
├── tests/             ← SDK tests only
└── logs/              ← session logs (gitignored, local only)
```

---

## License

MIT
