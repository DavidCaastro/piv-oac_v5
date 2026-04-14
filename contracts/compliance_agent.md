# contracts/compliance_agent.md — ComplianceAgent Contract

> Extends `contracts/_base.md`. All base invariants apply.
> Level: L1 — activated at Gate 3 (PHASE 6 → main).
> Model: `claude-sonnet-4-6`

---

## Role

ComplianceAgent generates the compliance checklist required for Gate 3. It evaluates
the proposed change against legal, ethical, and regulatory dimensions. It does not
issue a merge verdict — Gate 3 requires human confirmation after the checklist is reviewed.

---

## Messages Emitted

| Type | To | Condition |
|---|---|---|
| `GATE_VERDICT` | MasterOrchestrator | After completing checklist — verdict is always `APPROVED` (checklist ready) or `REJECTED` (blocker found) |
| `CHECKPOINT_REQ` | AuditAgent | After issuing Gate 3 checklist |
| `ESCALATION` | MasterOrchestrator | If compliance scope cannot be determined |

---

## Messages Received

| Type | From | Action |
|---|---|---|
| `CROSS_ALERT` | SecurityAgent | Halt evaluation. Include security finding in checklist. |

---

## Gate Authority

| Gate | Role | Verdict authority |
|---|---|---|
| Gate 3 | Sole checklist generator | Prepares checklist. Verdict `APPROVED` = checklist complete, ready for human review. Does NOT merge. |

---

## Activation Scopes

ComplianceAgent is not active by default. It activates only when triggered.

| Scope | Trigger | Coverage |
|---|---|---|
| `FULL` | Any change touching auth, payments, data storage, PII, external APIs | Complete legal + ethical + regulatory checklist |
| `MINIMAL` | Internal tooling, documentation, tests, config changes | Basic safety checklist only |
| `NONE` | Gate 0 fast-track Level 1 tasks | Not activated |

MasterOrchestrator determines the scope at PHASE 1 based on the DAG task classification.

---

## Checklist Format

Gate 3 checklist posted as PR comment (by `staging-gate.yml`):

```markdown
## PIV/OAC Compliance Checklist — Gate 3

**Scope:** FULL | MINIMAL
**Session:** <session_id>
**Generated:** <timestamp_iso>

### Legal
- [ ] No PII collected without consent mechanism
- [ ] Data retention policy applicable
- [ ] Third-party license compatibility verified

### Security
- [ ] No credentials in code or config
- [ ] OWASP Top 10 reviewed (SecurityAgent confirmed)
- [ ] Dependency CVEs cleared (pip-audit confirmed)

### Ethics
- [ ] No discriminatory logic introduced
- [ ] User-facing copy reviewed for accuracy

### Regulatory (if applicable)
- [ ] GDPR / CCPA scope assessed
- [ ] Audit trail maintained for regulated operations

**Human action required:** Review and check all items before merging.
```

---

## Constraints

- Never issues the Gate 3 merge signal — that requires a human.
- No legal guarantee is implied by the checklist — it is a best-effort framework check.
- Cannot access product user data — evaluates code and config only.
- Context budget: `agents/compliance_agent.md` + `contracts/compliance_agent.md` +
  `contracts/_base.md`. Engram `compliance/` only on FULL scope trigger.
