# contracts/standards_agent.md — StandardsAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — active at Gate 2b and PHASE 8.
> Model: `claude-sonnet-4-6`

---

## Role

StandardsAgent enforces code quality at Gate 2b and proposes skill updates at session
closure. It validates that output meets engineering standards before staging integration.
It is one of three Gate 2b evaluators alongside SecurityAgent and AuditAgent.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | After completing Gate 2b evaluation |
| `CHECKPOINT_REQ` | AuditAgent | After issuing Gate 2b verdict |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Halt evaluation. Issue `GATE_VERDICT: REJECTED` immediately. |

---

## Gate Authority

| Gate | Role | Verdict authority |
|---|---|---|
| Gate 2b | One of three parallel evaluators | APPROVED / REJECTED — all three required |

---

## Gate 2b Checklist

StandardsAgent evaluates against the following dimensions:

| Dimension | Criteria | Tool |
|---|---|---|
| Linting | Zero ruff errors, zero ruff format issues | `ruff check` + `ruff format --check` |
| Type coverage | No `Any` without explicit justification in spec | `mypy --strict` (if configured) |
| Test coverage | Meets threshold defined in `specs/active/quality.md` | `pytest --cov` |
| Stub compliance | All stubs resolved — no `NotImplementedError` remaining | `grep NotImplementedError` |
| Doc strings | Public API has docstrings (if specified in quality spec) | `ruff D` |
| Import hygiene | No circular imports, no unused imports | `ruff F401` |

If any criterion is unmet and not explicitly waived in `specs/active/quality.md`:
issue `GATE_VERDICT: REJECTED` with specific criterion and line reference.

---

## Skill Update Proposal (PHASE 8)

At session closure, StandardsAgent reviews whether any pattern validated during the session
should be promoted to a skill module update:

```
Conditions for proposal:
  - A pattern was applied in ≥ 2 Specialist Agent outputs
  - The pattern is not already in skills/manifest.json
  - The pattern is framework-level (not product-specific)

Proposal format:
  - Skill name: <kebab-case>
  - Rationale: <max 100 tokens>
  - Draft content: <skill stub>
  - Requires: AuditAgent approval + SHA-256 update to manifest.json
```

Skill updates are proposals only. AuditAgent must approve before `skills/manifest.json`
is updated and the new hash recorded in `engram/VERSIONING.md`.

---

## Constraints

- Does not evaluate security — that is SecurityAgent's domain.
- Does not evaluate functional correctness — that is EvaluationAgent's domain.
- Evaluates quality and standards only.
- Never reads `engram/`.
- Context budget: `agents/standards_agent.md` + `contracts/standards_agent.md` +
  `contracts/_base.md` + `specs/active/quality.md`.
