# skills/documentation-generation.md — Documentation Generation

## When to Load

When DocumentationAgent is generating docs in PHASE 7, or when StandardsAgent
is executing Gate 3 verification checks on any completed task.

---

## Gate 3 Blocking Rule

StandardsAgent at Gate 3 issues a hard REJECT (blocking, not advisory) if ANY
of the following conditions is detected:

**(A)** A Python module (any `.py` file modified in the task) is missing a
module-level docstring (the first statement of the file must be a string literal).

**(B)** Any public function or class (name does not begin with `_`) in a modified
file is missing a docstring.

**(C)** `README.md` exists but is missing one or more of the Required Sections
(see section below). If `README.md` does not exist at all for a package-level task,
that is also a blocking rejection.

**(D)** An OpenAPI spec file (`openapi.yaml` / `openapi.json`) is present but fails
schema validation against the OpenAPI 3.1 specification.

**(E)** Any Python file in the modified set references `.env` loading
(`dotenv`, `os.getenv`, `os.environ`) but `.env.example` is absent from the
repository root (or the package root for monorepos).

Gate 3 does not issue warnings for these items — they are blockers. The task
must be returned to the implementing agent for remediation before Gate 3 passes.

---

## Required Artifacts per Task Type

### All tasks (baseline, no exceptions)

- Docstrings on all public functions and classes (Google style, see format below)
- Module-level docstring in every modified `.py` file
- Inline comments for any non-obvious logic block (algorithm, regex, state machine)

### API tasks (any task exposing HTTP endpoints)

- OpenAPI 3.1 spec (auto-generated from code annotations or hand-written), stored
  in `docs/api/openapi.yaml`
- `.env.example` in repository root with all required environment variables listed;
  values must be redacted (use placeholder strings, not real values)
- `README.md` with an **API Usage** section containing at least one working `curl`
  example

### SDK / library tasks (any task modifying a public Python package)

- Full API reference covering all public symbols (functions, classes, constants),
  stored in `docs/api/<module>.md`
- A `CHANGELOG.md` entry for the release following the standard entry format
- Migration notes in `CHANGELOG.md` or a separate `MIGRATION.md` if the change
  introduces any breaking change (removed parameter, renamed symbol, changed return type)

### Framework meta tasks (PIV/OAC self-modification: sdk/, agents/, contracts/, sys/)

- Updated section in `_context_.md` describing what changed and why
- Updated skill file (`skills/<relevant>.md`) if agent behavior or routing changes
- Updated contract file (`contracts/<agent>.md`) if an agent's input/output
  contract changes
- No new narrative docs required unless the change affects operator onboarding

---

## Docstring Format (Google style)

All Python docstrings in the project use Google style. Do not use NumPy or
reStructuredText style.

```python
def function_name(param: type) -> return_type:
    """One-line summary ending with a period.

    Longer description if needed. Explain the purpose, not the implementation.
    Wrap at 88 characters.

    Args:
        param: Description of the parameter. Type is already in the signature;
            do not repeat it here.

    Returns:
        Description of the return value and its structure.

    Raises:
        ExceptionType: When this specific condition causes the exception.
        AnotherException: When a different condition occurs.
    """
```

**Class docstrings** go on the class, not on `__init__`. Describe the class
purpose and, if relevant, its key attributes.

**Module docstrings** go at the top of the file, before imports. One or two
sentences describing what the module provides.

---

## README Required Sections

The following sections are required, in this order. StandardsAgent checks for
each section header via regex (`^## <section>`). The check is case-insensitive.

1. **Project Identity** — name, version (or version badge), one-line description
2. **Installation** — pip install command or equivalent; system prerequisites
3. **Quick Start** — a working code example (≥5 lines) that can be copy-pasted
   and run without modification by a new user
4. **Configuration** — table or list of all environment variables with their
   default values and a brief description; reference `.env.example`
5. **API Reference** — either inline documentation or a link to `docs/api/`
6. **Contributing** — how to submit issues and pull requests; code style guide
7. **License** — SPDX identifier and link to `LICENSE` file

Sections may have subsections. Additional sections beyond these seven are allowed
but do not substitute for any required section.

---

## OpenAPI Validation Checklist

StandardsAgent runs this checklist deterministically against any OpenAPI spec
file present in the repository. All 10 items must pass for Gate 3 to clear.

1. `info.version` is present and follows semver format
2. Every path operation has a unique `operationId`
3. Every request body has a `schema` (not just a description)
4. Every response object has a `schema` or `$ref`
5. Security schemes are defined in `components/securitySchemes` if any endpoint
   uses authentication
6. Every request body includes at least one `example` or `examples` entry
7. Error responses for `400`, `401`, `403`, `404`, and `500` are documented on
   every endpoint where they are applicable
8. Every path parameter and query parameter has a `description` field
9. All endpoints are grouped with at least one `tag`
10. The `servers` list is populated with at least one entry (not left empty)

---

## StandardsAgent Verification Protocol

All checks are deterministic (Tier 1 — no LLM). StandardsAgent does not make
judgment calls; it applies the checklist and reports pass/fail with line references.

**(A) TODO/FIXME scan:** run `grep -rn "TODO\|FIXME"` on all modified files.
Emit `WARN(TODO_PRESENT, file, line)` for each hit. Warnings do not block Gate 3
but are included in the session telemetry report.

**(B) Docstring coverage:** for each modified `.py` file, parse the AST and count
public symbols (functions, classes, methods) without a docstring.
If count > 0: emit `REJECT(MISSING_DOCSTRINGS, file, symbol_list)`. Gate 3 blocked.

**(C) README section check:** load `README.md` and run regex match for each of
the 7 required section headers. If any are missing:
emit `REJECT(README_INCOMPLETE, missing_sections)`. Gate 3 blocked.

**(D) .env.example existence check:** if any modified Python file contains
`dotenv` imports or `os.getenv` / `os.environ` calls, assert `.env.example`
exists at the repository root. If absent:
emit `REJECT(ENV_EXAMPLE_MISSING)`. Gate 3 blocked.

**(E) Linting:** run `ruff check <modified_files>`. Any error (not warning) blocks
Gate 3 with `REJECT(LINT_ERROR, file, rule, line)`.

**(F) Dependency audit:** run `pip-audit --requirement requirements.txt` (or
equivalent lock file). Any known vulnerability with severity HIGH or CRITICAL
blocks Gate 3 with `REJECT(VULNERABLE_DEPENDENCY, package, cve)`.

---

## .env.example Consistency Check

Algorithm run by StandardsAgent as part of check (D) above.

```
1. Collect all .py files in the modified set
2. For each file, extract all strings matching:
       os.getenv("VAR_NAME")
       os.getenv("VAR_NAME", default)
       os.environ["VAR_NAME"]
       os.environ.get("VAR_NAME")
3. Build set: required_vars = union of all VAR_NAME matches
4. Load .env.example and extract all KEY= lines → defined_vars
5. missing = required_vars - defined_vars
6. If missing is non-empty:
       emit REJECT(ENV_EXAMPLE_INCONSISTENT, missing_vars=missing)
       Gate 3 blocked
```

Values in `.env.example` must be placeholders (e.g., `ANTHROPIC_API_KEY=your-key-here`),
never real credentials. StandardsAgent does not verify values, only key presence.

---

## Output Targets

| Content type | Target path | Model tier |
|---|---|---|
| API reference (structured, mechanical) | `docs/api/<module>.md` | Tier 2 (local) |
| Architecture explanations | `docs/architecture/<topic>.md` | Tier 3 (cloud) |
| User guides (conceptual) | `docs/guides/<guide>.md` | Tier 3 (cloud) |
| CHANGELOG entry | `CHANGELOG.md` (append) | Tier 2 (local) |
| Inline docstrings | Updated in-place in modified files | Tier 2 (local) |
| OpenAPI spec | `docs/api/openapi.yaml` | Tier 2 or hand-written |

---

## CHANGELOG Entry Format

```markdown
## [<version>] — <date>

### Added
- Feature description (task-id: auth-001)

### Changed
- Behavior change description (task-id: refactor-007)

### Fixed
- Bug description (issue-id: bug-042)

### Breaking
- Removed parameter `foo` from `bar()` — use `baz()` instead (migration: MIGRATION.md#v5.1)
```

---

## Sources (what DocumentationAgent reads)

- `specs/active/functional.md` — user-facing requirement descriptions
- `specs/active/architecture.md` — structural context
- Diff output from Gate 2b — actual changes made
- `engram/domains/<project>/` — domain context (if loaded)

Do not read `engram/security/` or `engram/audit/` — those are restricted to
SecurityAgent and AuditAgent respectively.

---

## What DocumentationAgent Does NOT Do

- Edit product source code (documentation artifacts only)
- Generate tests or test fixtures
- Make gate decisions (Gate 3 belongs to StandardsAgent, not DocumentationAgent)
- Load `engram/security/` or `engram/audit/`
- Auto-generate content without a source artifact to derive from — all generated
  documentation must be traceable to a spec, diff, or existing code comment
- Skip Gate 3 checks for any reason, including "urgent" or "hotfix" tasks — Gate 3
  is non-negotiable; urgency is not a bypass condition
- Approve its own output — DocumentationAgent produces artifacts; StandardsAgent
  independently verifies them at Gate 3

<!-- v5.1 — expanded from v4 audit -->
