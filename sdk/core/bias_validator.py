"""sdk/core/bias_validator.py — Tier 1 deterministic validator for BiasAuditAgent output.

Validates that an LLM-produced bias audit report contains all required sections
defined in skills/bias-audit.md §Output Section.

Required output sections (all mandatory for L2 proposals):
    ## Análisis de Sesgos y Dependencias
    Dependency table with at least one row (| Component | ... |)
    **Sesgos detectados:** checklist (4 items)
    **Red Team result:** PASSED | FAILED | INCONCLUSIVE
    **Multi-LLM audit:** CLEAN | ISSUES_FOUND | SKIPPED (...)
    **RAG precedence conflicts:** <value>

Enforcement:
    - validate_bias_output() runs BEFORE the bias audit result is accepted.
    - Any missing section → GATE_VERDICT(REJECTED) from BiasAuditAgent.
    - This is Tier 1: pure Python regex/string ops, zero LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class BiasValidationResult:
    """Result of a deterministic bias audit output check."""

    valid: bool
    missing_sections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Extracted values for downstream use (e.g. logging)
    red_team_result: str = ""        # PASSED | FAILED | INCONCLUSIVE | ""
    multi_llm_result: str = ""       # CLEAN | ISSUES_FOUND | SKIPPED | ""
    lock_in_risks: list[str] = field(default_factory=list)   # HIGH entries detected

    @property
    def rejected_reason(self) -> str:
        """Human-readable rejection reason for GATE_VERDICT rationale."""
        if self.valid:
            return ""
        return "BiasAudit output missing required sections: " + ", ".join(self.missing_sections)


# ---------------------------------------------------------------------------
# Compiled patterns (Tier 1 — no LLM)
# ---------------------------------------------------------------------------

# Section header — must appear verbatim (Spanish, as per skill spec)
_RE_SECTION_HEADER = re.compile(
    r"##\s+Análisis\s+de\s+Sesgos\s+y\s+Dependencias",
    re.IGNORECASE,
)

# Dependency table — at least one data row after the header row
_RE_TABLE_ROW = re.compile(
    r"^\|\s*(?![-:]+\s*\|)(.+?)\s*\|",  # row that is NOT a separator line
    re.MULTILINE,
)

# "Sesgos detectados:" checklist presence
_RE_SESGOS = re.compile(r"\*\*Sesgos\s+detectados:\*\*", re.IGNORECASE)

# Red Team result line
_RE_RED_TEAM = re.compile(
    r"\*\*Red\s+Team\s+result:\*\*\s*(PASSED|FAILED|INCONCLUSIVE)",
    re.IGNORECASE,
)

# Multi-LLM audit line
_RE_MULTI_LLM = re.compile(
    r"\*\*Multi-LLM\s+audit:\*\*\s*(CLEAN|ISSUES_FOUND|SKIPPED)",
    re.IGNORECASE,
)

# RAG precedence conflicts line
_RE_RAG = re.compile(r"\*\*RAG\s+precedence\s+conflicts:\*\*", re.IGNORECASE)

# Lock-in risk HIGH detection (warns even if overall valid)
_RE_LOCK_IN_HIGH = re.compile(r"\bHIGH\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_bias_output(text: str) -> BiasValidationResult:
    """Deterministically validate a BiasAuditAgent LLM output.

    Checks that the output contains all required sections per
    skills/bias-audit.md §Output Section.  Zero LLM calls — pure regex.

    Args:
        text: Raw text output from the BiasAuditAgent LLM call.

    Returns:
        BiasValidationResult with valid=True only if ALL sections present.
    """
    missing: list[str] = []
    warnings: list[str] = []
    red_team = ""
    multi_llm = ""
    lock_in_highs: list[str] = []

    # 1. Section header
    if not _RE_SECTION_HEADER.search(text):
        missing.append("## Análisis de Sesgos y Dependencias (section header)")

    # 2. Dependency table — look for header + separator + at least one data row
    #    The table must have the canonical columns
    if "| Component" not in text and "| component" not in text.lower():
        missing.append("Dependency table (| Component | Provider Dependency | Lock-in Risk | ...)")
    else:
        # Table present — count data rows (exclude separator lines)
        rows = _RE_TABLE_ROW.findall(text)
        # filter out header row itself
        data_rows = [r for r in rows if "Component" not in r and "---" not in r]
        if not data_rows:
            missing.append("Dependency table must have at least one component row")
        # check for HIGH lock-in without migration path
        if _RE_LOCK_IN_HIGH.search(text):
            # crude check: HIGH present — flag for downstream logging
            lock_in_highs.append("HIGH lock-in risk detected — verify migration path documented")

    # 3. Sesgos detectados checklist
    if not _RE_SESGOS.search(text):
        missing.append("**Sesgos detectados:** checklist")

    # 4. Red Team result
    m_rt = _RE_RED_TEAM.search(text)
    if not m_rt:
        missing.append("**Red Team result:** PASSED | FAILED | INCONCLUSIVE")
    else:
        red_team = m_rt.group(1).upper()
        if red_team == "FAILED":
            warnings.append(
                "Red Team result=FAILED: proposal did not survive semantic red team. "
                "Review BiasAuditAgent recommendation before proceeding."
            )

    # 5. Multi-LLM audit line
    m_ml = _RE_MULTI_LLM.search(text)
    if not m_ml:
        missing.append("**Multi-LLM audit:** CLEAN | ISSUES_FOUND | SKIPPED (...)")
    else:
        multi_llm = m_ml.group(1).upper()
        if multi_llm == "ISSUES_FOUND":
            warnings.append(
                "Multi-LLM audit=ISSUES_FOUND: hallucinated parameters or deprecated "
                "functions detected. Review before proceeding."
            )

    # 6. RAG precedence conflicts line
    if not _RE_RAG.search(text):
        missing.append("**RAG precedence conflicts:** <value>")

    return BiasValidationResult(
        valid=len(missing) == 0,
        missing_sections=missing,
        warnings=warnings,
        red_team_result=red_team,
        multi_llm_result=multi_llm,
        lock_in_risks=lock_in_highs,
    )


def section_present(text: str) -> bool:
    """Quick check: does the text contain the bias analysis section at all?

    Used by Gate 3 (StandardsAgent) to verify expert node outputs in L2 sessions.
    Less strict than validate_bias_output() — only checks header presence.
    """
    return bool(_RE_SECTION_HEADER.search(text))
