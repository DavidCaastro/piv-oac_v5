# skills/compliance-scoping.md — Compliance Scoping

## When to Load

When ComplianceAgent determines checklist scope for a Gate 3 review.

## Scope Classification

ComplianceAgent reads objective tags from `specs/active/functional.md` to determine scope:

| Tag | Scope | Checklist Size |
|---|---|---|
| `#data-privacy`, `#pii`, `#gdpr` | FULL | 15–20 items |
| `#authentication`, `#authorization` | FULL | 12–15 items |
| `#payment`, `#financial` | FULL + legal disclaimer | 18–25 items |
| `#api-change`, `#breaking-change` | MINIMAL + migration notes | 8–10 items |
| No sensitive tags | MINIMAL | 5–8 items |
| Internal tooling, docs only | NONE | 0 items (skip Gate 3) |

## Checklist Categories (FULL scope)

1. Functional requirements met (all specs/active/functional.md criteria)
2. Security review passed (Gate 2b APPROVED)
3. No hardcoded credentials (gitleaks clean)
4. Test coverage ≥ threshold (from specs/active/quality.md)
5. Documentation updated
6. Data handling compliant (if #data-privacy tag)
7. Auth flows reviewed (if #authentication tag)
8. CHANGELOG updated
9. AuditAgent session record complete
10. No regressions (EvaluationAgent score ≥ 0.80)

## Legal Disclaimer (always)

ComplianceAgent checklists are operational aids, not legal advice.
For regulated industries: consult qualified counsel.

## NONE Scope

If scope is NONE: ComplianceAgent does not generate a checklist.
Gate 3 is bypassed. Staging→main merge permitted with only Gate 2b.
AuditAgent records the bypass decision in `engram/audit/`.
