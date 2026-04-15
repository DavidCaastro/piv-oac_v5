# skills/evaluation-rubric.md — Evaluation Rubric

## When to Load

When CoherenceAgent scores ExpertAgent output at Gate 1 (pre-merge evaluation).

---

## 5 Dimensions

| Dimension | Weight | Description |
|---|---|---|
| FUNC (Functionality) | 0.35 | Does it fulfill all acceptance criteria in the spec? |
| SEC (Security) | 0.25 | No vulnerabilities, no hardcoded secrets, passes pip-audit |
| QUAL (Code Quality) | 0.20 | ruff clean, type hints, docstrings, no dead code |
| COH (Coherence) | 0.15 | Integrates cleanly with existing codebase, no interface conflicts |
| FOOT (Footprint) | 0.05 | Minimal changes, no unnecessary dependencies or over-engineering |

---

## Scoring Formula

```
weighted_score = FUNC*0.35 + SEC*0.25 + QUAL*0.20 + COH*0.15 + FOOT*0.05
```

Each dimension is scored 0.0 – 1.0. Weighted score range: 0.0 – 1.0.

| Score | Meaning |
|---|---|
| ≥ 0.90 | Excellent — approve |
| 0.80 – 0.89 | Good — approve with minor notes |
| 0.70 – 0.79 | Acceptable — approve with required fixes |
| < 0.70 | Reject — fundamental issues, must revise |

CoherenceAgent is information-only. Final Gate 1 decision belongs to the gate handler.

---

## Early Termination

If any single dimension scores **≤ 0.20 / 1.0**, the rubric SHORT-CIRCUITS:

```
→ Emit immediate GATE_VERDICT(REJECTED)
→ Do NOT evaluate remaining dimensions
→ Do NOT compute weighted_score
→ Log: "EARLY_TERMINATION: dimension=<DIM> score=<value> reason=<reason>"
```

**Rationale:** a critical failure in any one dimension is disqualifying regardless of other
scores. Example: SEC=0.0 due to a hardcoded credential cannot be offset by FUNC=1.0.
The early termination rule prevents false approvals and avoids unnecessary LLM calls.

Dimensions that trigger early termination if ≤ 0.20: SEC, QUAL, COH.
FUNC ≤ 0.20 also triggers early termination (objective not fulfilled).
FOOT ≤ 0.20 triggers early termination (catastrophic bloat).

---

## Dimension Detail: FUNC (Functionality)

Evaluates whether the output fulfills all acceptance criteria stated in functional.md.

| Score | Meaning |
|---|---|
| 1.0 | All acceptance criteria met; demonstrated by passing tests |
| 0.7 | Primary criteria met; edge cases incomplete or untested |
| 0.4 | Partial implementation; core path works, secondary paths missing |
| 0.2 | Significant gaps in required behavior; core path unreliable |
| 0.0 | Does not fulfill stated objective → EARLY_TERMINATION |

---

## Dimension Detail: SEC (Security)

Evaluates absence of vulnerabilities, secrets, and unsafe patterns.

| Score | Meaning |
|---|---|
| 1.0 | No security issues; OWASP checks pass; no hardcoded secrets detected |
| 0.7 | Minor issues only (non-critical OWASP findings, documentation-only exposure) |
| 0.4 | Medium issues present (input validation gaps, missing auth checks on non-critical paths) |
| 0.1 | High issues present (SQL injection possible, XSS possible, unsafe deserialization) |
| 0.0 | Critical issues (hardcoded credentials, RCE possible) → EARLY_TERMINATION |

Log format on early termination:
```
EARLY_TERMINATION: dimension=SEC score=0.0 reason=hardcoded_credential
```

---

## Dimension Detail: QUAL (Code Quality)

Evaluates code style, documentation, and maintainability.

| Score | Meaning |
|---|---|
| 1.0 | ruff clean (zero errors); full docstrings on public functions; readable; no TODOs |
| 0.7 | Minor style issues; mostly documented; ruff warnings only (no errors) |
| 0.4 | Significant style issues; partial documentation; ruff errors present but non-critical |
| 0.2 | Poor quality; difficult to maintain; missing most documentation |
| 0.0 | Unreadable or malformed code; ruff fails to parse → EARLY_TERMINATION |

---

## Dimension Detail: COH (Coherence)

Evaluates integration with the existing codebase and absence of interface conflicts.

| Score | Meaning |
|---|---|
| 1.0 | No conflicts with existing codebase; clean git diff; follows existing patterns |
| 0.7 | Minor interface inconsistencies (non-breaking); naming slightly off convention |
| 0.4 | Naming or pattern inconsistencies that require cleanup before merge |
| 0.2 | Significant structural conflicts; multiple integration points broken |
| 0.0 | Breaking changes to public interface without migration path → EARLY_TERMINATION |

---

## Dimension Detail: FOOT (Footprint)

Evaluates change scope and dependency overhead relative to the task size.

| Score | Meaning |
|---|---|
| 1.0 | Minimal changes; no unnecessary dependencies added; diff is tightly scoped |
| 0.7 | Small overhead; any additions are justified by the spec |
| 0.4 | Moderate overhead; some unjustified additions present |
| 0.2 | Significant bloat; many changes outside the node's declared scope |
| 0.0 | Catastrophic bloat (e.g., adds a 100 MB dependency for a 5-line task) → EARLY_TERMINATION |

---

## Tool Reference Sequence

CoherenceAgent runs tools in this mandatory order before LLM evaluation:

```
(1) grep      ← scan for hardcoded secrets/credentials patterns (SEC)
                patterns: API_KEY=, password=, token=, BEGIN PRIVATE KEY
                → SEC score directly affected by findings

(2) ruff      ← lint + format check (QUAL)
                ruff check . --output-format=json
                → parse error count; zero errors required for QUAL ≥ 0.7

(3) pytest    ← run assigned tests (FUNC)
                pytest --tb=short --co -q
                → collect and run; coverage check against quality.md threshold

(4) pip-audit ← dependency CVE scan (SEC)
                pip-audit --format=json
                → any CRITICAL CVE → SEC score ≤ 0.1

(5) LLM eval  ← evaluate FUNC, COH, FOOT dimensions
                runs ONLY if steps 1–4 complete without EARLY_TERMINATION trigger
                prompt receives: spec acceptance_criteria, git diff, tool outputs
```

If any tool in steps 1–4 is unavailable: emit `BLOCKED_BY_TOOL: <tool_name>` and halt.
Do not substitute or skip tool checks.

<!-- v5.1 — expanded Tier 4 -->
