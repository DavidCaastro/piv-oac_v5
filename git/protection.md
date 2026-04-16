# git/protection.md — Branch Protection Rules

Read by: `sys/git.md` (summary reference), GitHub repository administrators.

These rules must be configured in the GitHub repository settings.
They are enforced by GitHub — not by the SDK or CI workflows.

---

## Protection Matrix

Branch type definitions (Directive / Artifact) are in `git/topology.md §Branch Types`.

### Directive Branches

| Branch | Direct push | Force push | Delete | Require PR | Required approvals | CI gates required |
|---|---|---|---|---|---|---|
| `architect` | ✅ (human only) | ❌ | ❌ | ❌ | — | None (product CI does not apply) |
| `sec_ops` | ✅ (human only) | ❌ | ❌ | ❌ | — | None (product CI does not apply) |
| `piv-directive` | ❌ (SDK token only) | ❌ | ❌ | ❌ | — | None |

### Artifact Branches

| Branch | Direct push | Force push | Delete | Require PR | Required approvals | CI gates required |
|---|---|---|---|---|---|---|
| `main` | ❌ | ❌ | ❌ | ✅ | 1 human | Gate 3 (`staging-gate.yml`) |
| `staging` | ❌ | ❌ | ❌ | ✅ | 0 human | Gate 2b (`gate2b.yml`) |
| `feature/*` | ✅ (session agents only) | ❌ | ✅ (by SDK) | ✅ (subbranch→task) | 0 human | Gate 1 (`pre-merge.yml`) |
| `fix/*` | ✅ (session agents only) | ❌ | ✅ (by SDK) | ✅ | 0 human | Gate 1 (`pre-merge.yml`) |

---

## main — Full Protection

```yaml
# GitHub branch protection settings for main
require_pull_request_reviews:
  required_approving_review_count: 1
  dismiss_stale_reviews: true
  require_code_owner_reviews: false

required_status_checks:
  strict: true
  contexts:
    - "piv/staging-gate"      # staging-gate.yml must pass

restrictions:
  # No direct push from any actor — all changes via PR
  push_restrictions: []

allow_force_pushes: false
allow_deletions: false
```

**Note:** The 1 required human approval is Gate 3. ComplianceAgent generates the
checklist but cannot merge — a human must review and press the merge button.

---

## staging — CI-Protected

```yaml
require_pull_request_reviews:
  required_approving_review_count: 0   # Gate 2b verdict is sufficient

required_status_checks:
  strict: true
  contexts:
    - "piv/gate2b"            # gate2b.yml must pass

allow_force_pushes: false
allow_deletions: false
```

---

## feature/* and fix/* — Agent-Writable

```yaml
# No branch-level protection on feature/* — protection is at the PR level
required_status_checks:
  contexts:
    - "piv/pre-merge"         # pre-merge.yml (Gate 1) for subbranch → task PRs

allow_force_pushes: false
allow_deletions: true         # SDK prunes worktrees after Gate 1 merge
```

---

## Required Status Check Names

These must match the `name:` field in each workflow file:

| Check name | Workflow | Gate |
|---|---|---|
| `piv/gate2b` | `.github/workflows/gate2b.yml` | Gate 2b |
| `piv/pre-merge` | `.github/workflows/pre-merge.yml` | Gate 1 |
| `piv/staging-gate` | `.github/workflows/staging-gate.yml` | Gate 3 |

---

## CODEOWNERS (optional)

If a `CODEOWNERS` file is present, add at minimum:

```
# piv-directive is SDK-managed — no human owner
piv-directive  # (orphan branch — not subject to CODEOWNERS)

# sys/ files require review from a senior team member
/sys/  @team/senior-engineers
```

`CODEOWNERS` is optional for the framework but strongly recommended for production repos.
