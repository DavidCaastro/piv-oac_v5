# skills/documentation-generation.md — Documentation Generation

## When to Load

When DocumentationAgent is generating docs in PHASE 7.

## Output Targets

| Content type | Target | Model tier |
|---|---|---|
| API reference (structured, mechanical) | `docs/api/<module>.md` | Tier 2 (local) |
| Architecture explanations | `docs/architecture/<topic>.md` | Tier 3 (cloud) |
| User guides (conceptual) | `docs/guides/<guide>.md` | Tier 3 (cloud) |
| CHANGELOG entry | `CHANGELOG.md` (append) | Tier 2 (local) |
| Inline docstrings | Updated in product files | Tier 2 (local) |

## Docstring Format (Python)

```python
def method(param: Type) -> ReturnType:
    """One-line summary.

    Args:
        param: Description (type is already in signature).

    Returns:
        Description of return value.

    Raises:
        ErrorType: When this condition occurs.
    """
```

## Sources (what DocumentationAgent reads)

- `specs/active/functional.md` — user-facing requirement descriptions
- `specs/active/architecture.md` — structural context
- Diff output from Gate 2b — actual changes made
- `engram/domains/<project>/` — domain context (if loaded)

## What DocumentationAgent Does NOT Do

- Edit product source code (docs only)
- Generate tests
- Make gate decisions
- Load engram/security/ or engram/audit/

## CHANGELOG Entry Format

```markdown
## [<version>] — <date>

### Added
- Feature description (task-id: auth-001)

### Fixed
- Bug description (issue-id: bug-042)
```
