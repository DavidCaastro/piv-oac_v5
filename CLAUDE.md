# PIV/OAC v5.0 — Anthropic Claude Code Entrypoint

All operational instructions, agent contracts, verification requirements, and system rules
are defined in `sys/`.

**Start here:** read `sys/_index.md` to determine which files to load for your role and task.

Do not infer rules from this file. Do not act before reading `sys/_index.md`.
Do not read files outside your role's load list without explicit instruction.

---

## Execution Protocol

Two modes. Determine which applies before acting.

### Mode A — Product objective (feature, fix, refactor, research)

The user has given a development goal for a product codebase.
**Do NOT implement manually. Invoke the SDK and let the framework execute.**

```
Step 1 — Pre-flight (Tier 1, always):
    bash sys/bootstrap.sh validate
    → All BLOCKER checks must pass before proceeding.
    → If any BLOCKER fails, fix it and retry. Do not skip.

Step 2 — Run session (SDK executes full phase protocol):
    python -m sdk.cli run-async \
        --provider anthropic \
        --objective "<objective verbatim from user>"
    → AsyncSession handles PHASE 0–8.
    → Logs written to logs/sessions/<session_id>.jsonl
    → Index entry appended to logs/index.jsonl

Step 3 — Report result to user:
    Read and summarize AsyncSessionResult output.
    Surface warnings, gate verdicts, expert results.
    Do not re-implement what the SDK already did.
```

### Mode B — Framework meta-task (build, debug, document, analyze)

The user is working ON the framework itself (modifying sdk/, agents/, contracts/, sys/).
Read `sys/_index.md` → load files per role → act directly per the load table.
This mode does NOT invoke `python -m sdk.cli` — it modifies the framework code.

**When in doubt:** if the objective refers to a product feature → Mode A.
If the objective refers to the framework files themselves → Mode B.

---

For framework context and architecture: [`_init_.md`](_init_.md)
For build decisions and task status: [`_context_.md`](_context_.md)

---

## Branch Protocol

See `sys/_index.md §Session Branch Protocol` — applies to all providers.
