# sys/git.md — Git Connectivity and GitHub Actions Guidelines

> Two concerns in one file:
> 1. Git connectivity verification — what CHECK 2 and CHECK 3 in `_verify.md` execute.
>    sys/ owns this because git must be verified independently of the `git/` module.
> 2. GitHub Actions guidelines — what each workflow does and when it triggers.
>    The yml files live in `.github/workflows/`. This file explains their purpose only.

---

## Part 1 — Git Connectivity Verification

### CHECK 2: Remote reachable

```bash
GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code origin HEAD
```

Success: exit code 0 — remote responds.
Failure: exit code non-zero — network issue, wrong remote URL, or remote does not exist.

Diagnosis steps (for agent or human):
1. `git remote -v` — verify `origin` URL is correct.
2. `ping github.com` — verify network connectivity.
3. If URL is wrong: `git remote set-url origin <correct-url>`.

### CHECK 3: Credentials valid

Same command as CHECK 2 but with the expectation that it completes without an auth prompt.
`GIT_TERMINAL_PROMPT=0` ensures the command fails rather than waiting for input.

Failure modes:
- SSH key not loaded: `ssh-add ~/.ssh/id_ed25519`
- HTTPS token expired: update credential in system keychain or `.netrc`
- GitHub App token expired: re-authenticate via `gh auth login`

### Required GitHub Secrets (names only — values in Vault)

These secrets must exist in the repository's GitHub Actions secrets for CI workflows to run.

| Secret name | Used by | Purpose |
|---|---|---|
| `PIV_ANTHROPIC_KEY` | `gate2b.yml`, `staging-gate.yml` | LLM calls during gate evaluation |
| `PIV_AUDIT_TOKEN` | All workflows | AuditAgent write access to engram |
| `PIV_SECURITY_TOKEN` | `gate2b.yml` | SecurityAgent veto authority in CI |

Values are injected at workflow runtime. Never logged. Never echoed. Never stored in artifacts.

---

## Part 2 — GitHub Actions Guidelines

Workflow files live in `.github/workflows/`. This section explains what each does —
not how to write yml. For yml implementation, see the files directly.

### gate2b.yml — Post-CI Code Review Gate

**Trigger**: pull request from `feature/<task-id>/` to `staging`
**Purpose**: Gate 2b — final code review before staging integration

Sequence (mandatory order — no LLM until all tools pass):
1. `grep` pattern scan — detect hardcoded secrets, banned patterns
2. `pip-audit` — check dependencies for known CVEs
3. `semgrep` — static analysis against security and quality rules
4. All tools pass → SecurityAgent + AuditAgent + StandardsAgent LLM review
5. Any tool unavailable → `BLOCKED_BY_TOOL` status (workflow fails, no LLM verdict issued)

Outcome: APPROVED → merge to staging. REJECTED → PR blocked, rationale posted as comment.

### pre-merge.yml — Subbranch Coherence Check (Gate 1)

**Trigger**: pull request from `feature/<task-id>/expert-N` to `feature/<task-id>/`
**Purpose**: Gate 1 — CoherenceAgent verifies no semantic conflicts between experts

Sequence:
1. Compute diff between subbranch and task branch
2. CoherenceAgent reviews diff only (not full source files)
3. APPROVED → merge permitted. REJECTED → conflict details posted, Specialist Agent must resolve.

### staging-gate.yml — Staging to Main Gate (Gate 3)

**Trigger**: pull request from `staging` to `main`
**Purpose**: Gate 3 — compliance check + mandatory human approval

Sequence:
1. ComplianceAgent generates compliance checklist
2. Workflow posts checklist as PR comment and sets status to `waiting-for-human`
3. Human reviews checklist and approves PR manually
4. Merge permitted only after human approval — no automation can bypass this step

**This workflow cannot merge on its own. It can only block or prepare. The merge requires
a human pressing the merge button after reviewing the ComplianceAgent checklist.**

---

## Branch Protection Summary

For complete branch protection rules, see `git/protection.md`.

| Branch | Automated push | Force push | Merge without gate |
|---|---|---|---|
| `main` | ❌ | ❌ | ❌ (Gate 3 + human required) |
| `staging` | ❌ | ❌ | ❌ (Gate 2b required) |
| `feature/*` | ✅ (session agents) | ❌ | Gate 1 required for subbranch→task |
| `piv-directive` | SDK only | ❌ | SDK managed only |
