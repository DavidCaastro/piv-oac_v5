# sys/venv.md — Virtual Environment Directives

> Rules for Python virtual environment management in PIV/OAC v5.0.
> These are operational directives for agents requesting local execution —
> not a tutorial. If you need setup instructions, run `bash sys/bootstrap.sh setup`.

---

## Requirements

| Requirement | Value |
|---|---|
| Python minimum | 3.11 |
| venv location | `.venv/` at repository root |
| Activation | `source .venv/bin/activate` (Unix) / `.venv\Scripts\activate` (Windows) |
| Package manager | `pip` via `pyproject.toml` |
| Dev install | `pip install -e .[dev]` |

---

## Rules for Agents

### Before requesting any local execution

1. Verify venv is active: `python --version` must return `3.11+`.
2. If not active: do not attempt to activate it yourself — request `piv validate` first.
3. If CHECK 1 fails: request `bash sys/bootstrap.sh setup`.

### What agents may run inside the venv

Agents may request execution of:
- `bash sys/bootstrap.sh <command>` — all approved commands
- `pytest tests/ -v` (via `piv test`)
- `ruff check sdk/ tests/` (via `piv lint`)
- `python -m sdk.cli` (via `piv run`, Phase 2+)

Agents may NOT:
- Install packages directly (`pip install <anything>`) without a spec change to `pyproject.toml`
- Modify `pyproject.toml` dependencies without AuditAgent checkpoint
- Run arbitrary shell commands outside the approved command list

### Dependency changes

Any new dependency must:
1. Be added to `pyproject.toml` under the correct section (`dependencies`, `dev`, or `otel`)
2. Pass SecurityAgent review (no known CVEs via `pip-audit`)
3. Be reflected in a spec update before the next `piv setup`

---

## Environment Variables

Venv activation does not set PIV/OAC runtime variables. Those come from `.env` (gitignored).

```bash
# .env (local only — never commit)
PIV_PROVIDER=anthropic
PIV_VAULT_PATH=/path/to/vault
PIV_SESSION_DIR=.piv
ANTHROPIC_API_KEY=sk-...
```

The `.env.example` file (committed) lists required variable names with empty values
to guide new contributors. Values are never committed.

---

## Isolation Guarantee

`.venv/` is gitignored. It is never versioned, never shared, never referenced in specs
by absolute path. Agents always use relative paths from the repository root.
