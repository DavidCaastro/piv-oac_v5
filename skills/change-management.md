# skills/change-management.md — Change Management

## When to Load

Load when: any modification to framework files (`sdk/`, `agents/`, `contracts/`, `skills/`, `sys/`).
Loaded by: OrchestratorAgent (Mode B), StandardsAgent.
NOT required for: product code changes in user workspaces — those use Mode A and do not touch framework files.

---

## Change Classification

| Change Type | Risk Level | Required Approval | Rollback Plan Required |
|---|---|---|---|
| Skill content update (no interface change) | LOW | StandardsAgent auto-approve if tests pass | No |
| New skill file | LOW | StandardsAgent approval | No |
| Agent behavior change (`contracts/`) | MEDIUM | OrchestratorAgent + SecurityAgent | Yes |
| SDK API change (public interface) | HIGH | All agents gate review + user confirmation | Yes |
| `sys/` or `CLAUDE.md` change | CRITICAL | User explicit approval | Yes |
| Load table change (`_index.md`) | CRITICAL | User explicit approval + security review | Yes |

Classification is determined before any file is opened. If the change type is unclear, treat it as one level higher than the best estimate.

---

## Pre-Change Checklist

Before any framework modification, complete all items:

- [ ] Read the current file(s) fully before making any edit.
- [ ] Check if the change affects `skills/manifest.json` — any skill edit requires a hash update in the same commit.
- [ ] Verify no circular dependency is introduced in `sdk/core/loader.py` `_AUTHORIZED_LOADS`.
- [ ] Check if a contract change requires a matching agent markdown update (`contracts/` and `agents/` must stay in sync).
- [ ] Identify all files that import or reference the changed module. List them explicitly before editing.
- [ ] Confirm the change classification (see table above) and ensure the correct approval flow is followed.
- [ ] For HIGH/CRITICAL changes: confirm a rollback plan exists before the first edit.

Do not begin editing until all applicable checkboxes are resolved.

---

## Skill Knowledge Change Triggers

A skill file MUST be updated when any of the following conditions apply:

1. The behavior it describes has changed in SDK code (any `.py` file in `sdk/`).
2. A new PMIA message type is added that the skill should handle or reference.
3. A new gate is added or an existing gate changes scope in a way that affects the skill's phase coverage.
4. An agent contract changes the interface or message types that the skill documents.

**Detection mechanism:** StandardsAgent at Gate 3 compares skill content against the corresponding contract. Any contradiction — a skill describing a behavior that the contract no longer specifies — is flagged as a `STANDARDS_VIOLATION` and blocks Gate 3 approval.

When a trigger condition is met, the skill update must be included in the same PR as the SDK/contract change. Separate PRs for skill updates are not acceptable for HIGH/CRITICAL changes.

---

## StandardsAgent Approval Workflow

For LOW and MEDIUM risk changes:

1. The proposing agent presents the full diff of the intended change.
2. StandardsAgent runs the deterministic checklist:
   - Markdown syntax valid (no broken headings, tables, or code blocks).
   - All file references in the diff resolve to existing paths.
   - `skills/manifest.json` hash is updated if a skill was changed.
   - No contradiction between `contracts/` and `agents/` for the affected role.
3. StandardsAgent issues `GATE_VERDICT(APPROVED)` or `GATE_VERDICT(REJECTED)` with a specific reason.
4. On `APPROVED`: the change is committed, `skills/manifest.json` is updated, and `_context_.md` is updated in the same commit.
5. On `REJECTED`: the proposing agent receives the full rejection reason. The agent must address all stated issues before re-submitting. Re-submission without addressing every point is a protocol violation.

For HIGH and CRITICAL changes, this workflow applies AND requires additional approvals per the classification table.

---

## Rollback Protocol

For HIGH and CRITICAL changes that require a rollback plan:

1. **Before the change:** Create an isolated checkpoint — either `git stash` or a checkpoint commit on a dedicated branch. Record the commit SHA.
2. **Apply the change** and run all applicable tests and gate checks.
3. **If any gate fails:**
   - Run `git revert <checkpoint-sha>` to restore the pre-change state.
   - Do NOT manually undo individual edits — always use `git revert` for traceability.
4. **Document the rollback** in `_context_.md` §27 Open Decisions: state what was attempted, why it was reverted, and what must change before a retry.
5. Emit `CHECKPOINT_REQ` after rollback completion. AuditAgent must acknowledge before any new change attempt on the same scope.

---

## Manifest Integrity

After ANY edit to a file in `skills/*.md`:

1. Recalculate the SHA-256 hash of the edited file:

```python
import hashlib, pathlib
hash = hashlib.sha256(pathlib.Path("skills/<name>.md").read_bytes()).hexdigest()
```

2. Update the corresponding entry in `skills/manifest.json`.
3. Run `bash sys/bootstrap.sh validate` and confirm CHECK 6 passes with no errors.
4. Include the `manifest.json` update in the same commit as the skill change. These are never committed separately.

Committing a skill change without updating `manifest.json` in the same commit is a protocol violation. StandardsAgent will reject the PR at Gate 2b.

---

## `_context_.md` Update Rule

Any framework change that affects architecture, behavior, or task status MUST update `_context_.md` in the same commit:

- **§28 Task Tracker:** Mark the completed item as done, or add a new item if the change introduces new work.
- **Relevant section:** Update the section's description to accurately reflect the new state. Do not leave stale descriptions.
- **Last updated field:** Increment the session number and update the date.

If a change is made and `_context_.md` is not updated, StandardsAgent will flag the inconsistency at Gate 3. This is a blocking finding — it will prevent Gate 3 approval until resolved.

---

## Contracts ↔ Agents Sync Rule

`contracts/<agent>.md` and `agents/<agent>.md` serve distinct and complementary roles:

- `contracts/`: defines what the agent **must do** — behavior contract, gate authority, PMIA message types it produces and consumes.
- `agents/`: defines who the agent **is** — role description, model assignment, permissions, skill load list, phase assignments.

**Sync requirement:** These two files must be consistent at all times.

- If `contracts/` adds, removes, or renames a PMIA message type for an agent → `agents/` must update its PMIA section to match.
- If `agents/` changes the agent's phase assignments → `contracts/` must be reviewed for gate scope consistency.

**StandardsAgent check:** At Gate 3, StandardsAgent verifies that every `MessageType` listed in `contracts/<agent>.md` is also listed in the corresponding `agents/<agent>.md` PMIA section. Any mismatch is a blocking finding.

---

## Restrictions

The following actions are unconditionally prohibited:

- **NEVER** modify `engram/` audit records after they are written. All engram records are immutable.
- **NEVER** skip `bash sys/bootstrap.sh validate` before any Mode A session invocation.
- **NEVER** commit a skill file change without updating `skills/manifest.json` in the same commit.
- **NEVER** change `sys/_index.md` Load Table without explicit user approval, regardless of how minor the change appears.
- **NEVER** rename a public SDK function (any function in `sdk/` callable by agents) without adding migration notes to `skills/documentation-generation.md` and `_context_.md` §28.

Violation of any restriction is a `PROTOCOL_VIOLATION` that triggers `ESCALATION(reason=PROTOCOL_VIOLATION)` to the PMIABroker.

<!-- v5.1 — new skill, restoring framework governance from v4 change-management -->
