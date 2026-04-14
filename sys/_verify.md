# sys/_verify.md — Pre-flight Verification Contract

> This file defines every check that `bootstrap.sh` must run before routing any agent
> to `sdk/`. Checks are ordered. Blockers halt execution immediately. Warnings log and
> continue. No agent proceeds to `sdk/` until all BLOCKER checks pass.

---

## Verification Sequence

### CHECK 1 — Python venv active `BLOCKER`

Verify that a Python virtual environment is active and meets the minimum version requirement.

```
Required: Python >= 3.11
Test:     python --version | grep -E "3\.(1[1-9]|[2-9][0-9])"
Fail:     print "BLOCKER: venv not active or Python < 3.11" and exit 1
Pass:     continue to CHECK 2
```

Agent instruction: if CHECK 1 fails, run `bash sys/bootstrap.sh setup` and retry.
Do not proceed past this check without a passing venv.

---

### CHECK 2 — git remote reachable `BLOCKER`

Verify that the `origin` remote is reachable.

```
Test:     git ls-remote --exit-code origin HEAD
Fail:     print "BLOCKER: git remote 'origin' unreachable" and exit 1
Pass:     continue to CHECK 3
```

---

### CHECK 3 — git credentials valid `BLOCKER`

Verify that authentication to the remote succeeds without interactive prompt.

```
Test:     git ls-remote --exit-code origin HEAD (with GIT_TERMINAL_PROMPT=0)
Fail:     print "BLOCKER: git credentials invalid or missing" and exit 1
Pass:     continue to CHECK 4
Note:     CHECK 2 and CHECK 3 use the same command — if CHECK 2 passes but
          CHECK 3 fails, the remote is reachable but auth is broken.
```

---

### CHECK 4 — required environment variables present `BLOCKER`

Verify that all mandatory runtime variables exist in the environment.
This check validates presence only — values are never logged.

```
Required variables:
  PIV_PROVIDER       ← active provider name (anthropic | openai | ollama)
  PIV_VAULT_PATH     ← path to MCP Vault socket or config
  PIV_SESSION_DIR    ← path to .piv/ session directory

Test:     for each var: [ -n "${VAR}" ] || exit 1
Fail:     print "BLOCKER: missing env var: <VAR_NAME>" and exit 1
Pass:     continue to CHECK 5
```

---

### CHECK 5 — provider API token present `BLOCKER` (per active provider)

Verify that the credential for the active provider exists. Value is never logged.

```
If PIV_PROVIDER=anthropic:  [ -n "${ANTHROPIC_API_KEY}" ]
If PIV_PROVIDER=openai:     [ -n "${OPENAI_API_KEY}" ]
If PIV_PROVIDER=ollama:     curl -sf http://${OLLAMA_HOST:-localhost}:11434/api/tags

Fail:     print "BLOCKER: provider credential missing for <PIV_PROVIDER>" and exit 1
Pass:     continue to CHECK 6
```

---

### CHECK 6 — skills manifest SHA-256 `BLOCKER`

Verify that `skills/manifest.json` exists and its hash matches the expected value
stored in `engram/VERSIONING.md`. Any mismatch indicates tampering or corruption.

```
Test:     sha256sum skills/manifest.json | compare with engram/VERSIONING.md#skills-manifest
Fail:     print "BLOCKER: skills manifest hash mismatch — possible tampering"
          notify SecurityAgent (write CROSS_ALERT to .piv/alerts/)
          exit 1
Pass:     continue to CHECK 7
Note:     On first run (engram/VERSIONING.md does not exist): compute and store hash,
          treat as PASS, log as WARNING "initial manifest baseline established".
```

---

### CHECK 7 — session state `WARNING`

Detect unclosed sessions from a prior interrupted run.

```
Test:     ls .piv/active/ 2>/dev/null | grep -q ".json"
If found: print "WARNING: unclosed session found in .piv/active/"
          print "  session_id: <id>"
          print "  Run 'piv-oac resume' to continue or 'piv-oac discard' to clear."
          log to .piv/alerts/warn_unclosed_session_<timestamp>.log
          continue (do not block)
```

---

### CHECK 8 — stale worktrees `WARNING`

Detect worktree entries in `worktrees/` that are no longer registered in git.

```
Test:     diff <(ls worktrees/ 2>/dev/null) <(git worktree list --porcelain | grep "worktree" | awk '{print $2}')
If stale: print "WARNING: stale worktree paths detected:"
          print "  <path>"
          print "  Run 'piv wt:prune' to clean up."
          continue (do not block)
```

---

## Required Variables Reference

| Variable | Purpose | Source |
|---|---|---|
| `PIV_PROVIDER` | Active inference provider | `.env` or shell export |
| `PIV_VAULT_PATH` | MCP Vault socket / config path | `.env` or shell export |
| `PIV_SESSION_DIR` | `.piv/` directory path (defaults to `.piv/`) | `.env` or shell export |
| `ANTHROPIC_API_KEY` | Anthropic credential (if provider=anthropic) | `.env` or shell export |
| `OPENAI_API_KEY` | OpenAI credential (if provider=openai) | `.env` or shell export |
| `OLLAMA_HOST` | Ollama host (if provider=ollama, default: localhost) | `.env` or shell export |

Values are read at session init. Never passed to agents. Never logged. Never committed.

---

## Pass Criteria

All 6 BLOCKER checks must pass. WARNING checks (7, 8) do not block execution.
A clean verification prints:

```
[PIV/OAC] Pre-flight verification
  CHECK 1  venv active (Python 3.11.x)          PASS
  CHECK 2  git remote reachable                  PASS
  CHECK 3  git credentials valid                 PASS
  CHECK 4  env vars present (3/3)               PASS
  CHECK 5  provider token present (anthropic)    PASS
  CHECK 6  skills manifest SHA-256               PASS
  CHECK 7  session state                         PASS (no unclosed sessions)
  CHECK 8  stale worktrees                       PASS (none found)
  ──────────────────────────────────────────────────
  All checks passed. Routing to sdk/.
```
