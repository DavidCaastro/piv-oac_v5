# skills/spec-writing.md — Spec Writing

## When to Load

When SpecWriter is writing PHASE 0.2 output or when reviewing spec quality.

---

## Output Files

```
specs/active/
├── functional.md    ← ALWAYS written (Level 1 and 2)
├── architecture.md  ← Level 2 complex only
└── quality.md       ← ALWAYS written
```

**Immutability rule:** once the user confirms specs (`confirm_specs=True` path, step 3 below),
all files under `specs/active/` are IMMUTABLE for the duration of the session.
No agent, orchestrator, or handler may overwrite or patch them in-place.
Amendment requires a new session (see Spec Amendment Protocol).

---

## functional.md Fields

### Required fields

```yaml
objective: one-sentence goal           # maps to {{objective}}
scope:
  - concrete deliverable 1             # maps to {{scope}}
  - concrete deliverable 2
acceptance_criteria:
  - criterion that can be tested mechanically   # maps to {{acceptance_criteria}}
```

### Optional fields

```yaml
constraints:
  - constraint that limits implementation       # maps to {{constraints}}
out_of_scope:
  - item explicitly excluded                    # maps to {{out_of_scope}}
tasks:
  - task block (see Task Block Format)          # maps to {{tasks}}
```

### Template variable mapping (specs/_templates/functional.md.tpl)

| Field | Template variable |
|---|---|
| `objective` | `{{objective}}` |
| `scope` | `{{scope}}` |
| `acceptance_criteria` | `{{acceptance_criteria}}` |
| `constraints` | `{{constraints}}` |
| `out_of_scope` | `{{out_of_scope}}` |
| `tasks` | `{{tasks}}` |
| `session_id` | `{{session_id}}` |
| `created_at` | `{{created_at}}` |
| `level` | `{{level}}` |

### Field validation rules

| Field | Rule |
|---|---|
| `objective` | Must be ≥ 20 characters. SpecWriter raises `SpecValidationError` if shorter. |
| `scope` | Must have ≥ 1 item. Empty scope list is rejected before write. |
| `acceptance_criteria` | Must have ≥ 1 item. SpecWriter raises `SpecValidationError` if empty. |
| `constraints` | Optional. Must not duplicate items already listed in `acceptance_criteria`. |
| `tasks[*].node_id` | Must be unique within the spec. Duplicate node_ids → `SpecValidationError`. |
| `tasks[*].depends_on` | All referenced node_ids must exist within the same spec. |

---

## Spec Confirmation Workflow

Full sequence executed in PHASE 0.2 → PHASE 0.3 boundary:

```
(1) Interview completes (PHASE 0.1)
        ↓
    SpecWriter.write_functional(answers)
        → validates all required fields
        → renders functional.md.tpl with 9 variables
        → writes to specs/active/functional.md
        → writes to specs/active/quality.md
        → writes to specs/active/architecture.md (Level 2 only)

(2) if confirm_specs=True:
        → display written file list to user (paths + line counts)
        → call handler.confirm("Confirm specs? [y/N]")

(3) User confirms (y):
        → session_state["specs_confirmed"] = True
        → specs/active/ files marked immutable in session state
        → proceed to PHASE 1 (DAG build)

(4) User rejects (N or timeout):
        → return AsyncSessionResult(status="spec_rejected")
        → no DAG is built
        → no further LLM calls are made
        → no cost incurred beyond PHASE 0

(5) if confirm_specs=False (CI/programmatic mode):
        → auto-proceed: session_state["specs_confirmed"] = True
        → no prompt shown, no handler.confirm() called
        → proceed directly to PHASE 1
```

The `confirm_specs` parameter is set in `run_async()`. Default: `True` (interactive).

---

## Task Block Format

SpecDAGParser accepts task blocks in `functional.md` using this exact format:

```
### task::<node_id>
- **domain**: <string>
- **description**: <string>
- **depends_on**: <comma-separated node_ids or (none)>
- **files_in_scope**: <comma-separated paths or (tbd)>
- **experts**: <integer ≥ 1>
```

### node_id rules

| Rule | Detail |
|---|---|
| Case | kebab-case only (lowercase, hyphens) |
| Characters | Alphanumeric and hyphens only — no underscores, dots, or spaces |
| Length | Maximum 40 characters |
| Uniqueness | Must be unique within the spec — duplicate node_ids → parse error |

### Field rules for task blocks

| Field | Rule |
|---|---|
| `domain` | Free string; must match an available ExpertAgent domain |
| `description` | Free string; used as ExpertAgent prompt context |
| `depends_on` | `(none)` for root nodes; comma-separated node_ids otherwise |
| `files_in_scope` | `(tbd)` if unknown at spec time; comma-separated paths otherwise |
| `experts` | Integer ≥ 1; controls parallelism within the node |

---

## Spec Amendment Protocol

When the user wants to change specs after confirmation (post-session):

1. A confirmed spec cannot be edited in-place. No patch, no append.
2. User must trigger a new `run_async()` call with updated interview answers.
3. Before the new session starts, the framework:
   - Archives the previous spec: `specs/archive/<previous_session_id>_functional.md`
   - Archives quality and architecture specs under the same prefix
   - Generates a new `session_id` for the amended run
4. The amended session proceeds from PHASE 0.1 (interview) as a full new session.
5. Archived specs are retained but not used by any agent in the new session.

---

## _derive_tasks_from_scope() Behavior

Used as Tier 1 fallback when no explicit `tasks` key is present in interview answers.

**Heuristic:**

1. Takes the `scope` list from interview answers.
2. Splits each scope item on commas, semicolons, and newlines → flat list of items.
3. Each item becomes one sequential task node:
   - `node_id`: lowercase slug of item text, max 40 chars (spaces → hyphens, strip special chars)
   - `depends_on`: the node_id of the previous item (first item has no dependency)
   - `domain`: inferred from item text (fallback: `"general"`)
   - `experts`: 1
   - `files_in_scope`: `(tbd)`
4. Result: a linear chain DAG (no parallelism) derived purely from scope.
5. This heuristic is replaced if the spec author writes explicit `### task::` blocks.

---

## Spec Quality Checklist

- [ ] Objective is specific and measurable
- [ ] Objective is ≥ 20 characters
- [ ] Scope items are achievable in one session
- [ ] Scope has ≥ 1 item
- [ ] Acceptance criteria are testable without human judgment
- [ ] Acceptance criteria has ≥ 1 item
- [ ] No contradictions between functional.md and architecture.md
- [ ] Out-of-scope items explicitly listed (prevents scope creep)
- [ ] Spec does not duplicate acceptance_criteria content inside constraints
- [ ] Each task node_id is unique within the spec
- [ ] All depends_on references resolve to node_ids that exist in the same spec

---

## architecture.md (Level 2 complex)

Contains structural decisions: patterns chosen, APIs designed, data model,
third-party integrations. Written in plain English sections.
No implementation details — architecture, not code.

---

## quality.md

```yaml
coverage_threshold: 80   # percent minimum
acceptance_checks:
  - All assigned tests pass
  - ruff check passes (zero errors)
  - No NotImplementedError remaining
```

<!-- v5.1 — expanded Tier 4 -->
