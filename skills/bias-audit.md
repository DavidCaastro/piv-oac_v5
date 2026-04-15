# skills/bias-audit.md — Bias Audit

## When to Load

Load when: BiasAuditAgent is active. Also loaded by OrchestratorAgent when complexity=L2
and any architectural decision involves provider selection, library choice, or pattern adoption.

---

## Core Mission

- Detect and neutralize "statistical comfort" biases in technical proposals — patterns that
  emerge because they are statistically over-represented in LLM training data, not because
  they are the best fit for the task at hand.
- Prevent lock-in to proprietary ecosystems without an explicit comparative analysis.
- Guarantee that the statistical popularity of a solution is never its sole justification.
- Preserve the deterministic logic of specs and contracts over the LLM's "general knowledge."

---

## Four Audit Directives

### Directive 1 — Ecosystem Neutrality (Anti-Lock-in)

Prioritizing proprietary cloud-provider services without an explicit comparison is prohibited.
For EVERY architectural decision, list at least one open-source or alternative-provider option.

**Mandatory comparison format:**

```
Proposed: <solution>
Alternatives considered:
  - <open-source alternative>: <tradeoff>
  - <competing-provider alternative>: <tradeoff>
Selection rationale: <why proposed > alternatives for THIS specific task>
Lock-in risk: LOW | MEDIUM | HIGH
Migration path if lock-in: <description>
```

**Lock-in risk classification:**

| Risk Level | Definition | Example |
|---|---|---|
| LOW | Standard protocol; easy to swap with minimal migration cost | PostgreSQL vs. MySQL; both speak SQL |
| MEDIUM | API-specific but abstracted within the SDK layer | Anthropic provider behind ProviderRouter |
| HIGH | Deep integration where provider primitives wire directly to business logic | AWS Lambda with IAM roles embedded in application logic |

---

### Directive 2 — Anti-Popularity Validation (Semantic Red Teaming)

If the proposed solution matches the most common pattern found in training data,
BiasAuditAgent MUST provide a technical justification before confirming. Performing
this justification is not optional.

**Semantic Red Teaming protocol — 5 steps:**

1. Identify the initial proposal.
2. Classify whether it is the "path of least resistance": does this pattern appear in
   the top results of a Google search for the general problem type?
3. Formulate the strongest possible counter-argument against the proposal.
4. Evaluate whether that counter-argument is valid in this specific context.
5. Only if the proposal survives the red team → confirm. Otherwise → revise or escalate.

**Patterns that ALWAYS require red teaming:**

- Redux for frontend state management
- AWS Lambda as the default compute choice
- Docker as the default deployment unit (vs. bare metal or alternative runtimes)
- React for simple or static applications
- Microservices architecture for a team of two or fewer engineers

**Output format:**

```
Red Team Result: PASSED | FAILED | INCONCLUSIVE
Proposed pattern: <pattern>
Strongest counter-argument: <argument>
Response to counter: <why the proposal still holds, or what changed>
Final recommendation: confirmed | revised | escalated
```

---

### Directive 3 — Multi-LLM Interoperability Audit

For L2-complexity tasks: architecture proposed by Model A must be validated by Model B.

**Cross-audit criteria:**

- Parameter hallucinations: function or method that does not exist in the library at the stated version
- Deprecated functions: marked deprecated in a recent release of the dependency
- Syntactic bias: preference for syntax or idioms specific to Model A's dominant training provider
- Implicit model assumptions: e.g., "Python 3.8+ assumed," "pip install as the only package manager"

**Protocol:**

1. Model A (primary) proposes the architecture.
2. BiasAuditAgent extracts:
   - (a) All external dependencies with version constraints
   - (b) All API calls with their parameter signatures
   - (c) All architectural patterns adopted
3. Validate extracted items against:
   - (a) Official library documentation
   - (b) PyPI latest stable version (or npm, cargo, etc. as applicable)
   - (c) Published deprecation notices
4. Model B (auditor) reviews the extracted items — emit `CROSS_ALERT` if any
   contradiction is found between the proposal and the validated reference.

**Audit result format:**

```
Multi-LLM Audit: CLEAN | ISSUES_FOUND
Parameters validated: <N>
Hallucinated params: [list or "none"]
Deprecated functions: [list or "none"]
Provider-biased syntax: [list or "none"]
Recommendation: proceed | revise | block
```

---

### Directive 4 — Deterministic Logic Preservation

Design documents in `specs/`, `contracts/`, and `sys/` hold absolute hierarchical
precedence over any "general knowledge" the model carries from training.

If the model detects a contradiction between its training and a framework guideline:
MUST REPORT it immediately. Silent resolution is a protocol violation.

**Contradiction report format:**

```
[BIAS_CONFLICT] Detected contradiction:
My training suggests: <what the model knows>
Framework spec states: <what the spec says>
Resolution: Framework spec takes precedence.
Action taken: following spec | escalating for human review
```

**Trigger conditions:** any proposal that contradicts the content of `contracts/`,
`agents/`, `specs/active/`, or `sys/`.

---

## Output Section: Bias & Dependency Analysis

Every technical proposal produced within the framework during L2 sessions MUST end with
the following section. Absence of this section in an L2 proposal is grounds for
`GATE_VERDICT: REJECTED`.

```markdown
## Análisis de Sesgos y Dependencias

| Component | Provider Dependency | Lock-in Risk | Open-Source Alternative |
|---|---|---|---|
| <component> | <provider / library> | LOW / MEDIUM / HIGH | <alternative> |

**Sesgos detectados:**
- [ ] Popularidad estadística: <yes / no — detail>
- [ ] Preferencia de proveedor: <yes / no — detail>
- [ ] Función obsoleta: <yes / no — detail>
- [ ] Alucinación de parámetro: <yes / no — detail>

**Red Team result:** PASSED | FAILED | INCONCLUSIVE
**Multi-LLM audit:** CLEAN | ISSUES_FOUND | SKIPPED (complexity < L2)
**RAG precedence conflicts:** <none | list>
```

---

## Integration with PIV/OAC Gates

| Gate | BiasAuditAgent Role |
|---|---|
| Gate 0 (complexity) | BiasAuditAgent activates for tasks classified L2 |
| Gate 1 (coherence) | BiasAuditAgent adds the Bias & Dependency Analysis section to the CoherenceAgent review package |
| Gate 2a (security) | BiasAuditAgent provides lock-in risk assessment to SecurityAgent |
| Gate 3 (standards) | BiasAuditAgent confirms that all L2 proposals contain the required output section |

---

## PMIA Message Protocol

| Message | Condition |
|---|---|
| `CROSS_ALERT` (severity=MEDIUM) | Provider lock-in risk=HIGH without documented justification or migration path |
| `CROSS_ALERT` (severity=HIGH) | Hallucinated parameter or deprecated function detected in any proposal |
| `ESCALATION` (reason=PROTOCOL_VIOLATION) | Proposal skips Semantic Red Teaming on a known popular pattern |
| `GATE_VERDICT` (verdict=REJECTED) | Bias & Dependency Analysis section missing from an L2 proposal |
| `CHECKPOINT_REQ` | After completing a full four-directive audit of any proposal |

All messages are HMAC-SHA256 signed and routed through the AuditAgent broker.
Max payload: 300 tokens (base protocol limit — see `contracts/_base.md`).

---

## What This Skill Does NOT Do

- Does not block proposals solely because they use a popular solution — it requires
  technical justification before confirming, but a justified popular solution is valid.
- Does not replace SecurityAgent — BiasAuditAgent complements it from the perspective of
  vendor bias and ecosystem dependency, not security threats.
- Does not audit product code in the user workspace — scope is limited to architectural
  decisions and proposals produced within framework sessions.
- Does not execute code or commands — analysis is performed on proposals and documents only.

<!-- v5.1 — new skill: BiasAuditAgent — anti-lock-in + red-team + multi-llm audit -->
