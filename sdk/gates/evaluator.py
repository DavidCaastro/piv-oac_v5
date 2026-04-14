"""sdk/gates/evaluator.py — GateEvaluator (Tier 1, deterministic gate logic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GateVerdict(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class GateType(str, Enum):
    GATE_0 = "GATE_0"    # Fast-track: SecurityAgent only, 60s budget
    GATE_1 = "GATE_1"    # Subbranch merge: CoherenceAgent
    GATE_2 = "GATE_2"    # Plan review: Security + Audit + Coherence
    GATE_2B = "GATE_2B"  # Post-CI code review: EvaluationAgent + StandardsAgent
    GATE_3 = "GATE_3"    # Human-only merge to main: ComplianceAgent checklist


@dataclass
class GateContext:
    """Evaluation context passed to the gate evaluator."""

    gate: GateType
    session_id: str
    agent_id: str
    payload: dict[str, Any]
    consecutive_rejections: int = 0


@dataclass
class GateResult:
    verdict: GateVerdict
    gate: GateType
    rationale: str
    triggered_circuit_breaker: bool = False
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)


class GateEvaluator:
    """Deterministic gate routing and circuit-breaker logic.

    All gate decisions are Tier 1: rule-based checks on the payload.
    Agents supply their verdict; this class enforces protocol invariants.

    Circuit breaker (_context_.md §15 PMIA v5.0):
        3 consecutive GATE_VERDICT: REJECTED → session moved to .piv/failed/
    """

    CIRCUIT_BREAKER_THRESHOLD = 3

    def evaluate(self, ctx: GateContext, proposed_verdict: GateVerdict) -> GateResult:
        """Apply invariant checks and return the final gate result.

        Args:
            ctx: Contextual data for this gate evaluation.
            proposed_verdict: The verdict proposed by the controlling agent.

        Returns:
            GateResult with the final, invariant-enforced verdict.
        """
        checks_passed: list[str] = []
        checks_failed: list[str] = []

        # --- Invariant: session_id must be present ---
        if ctx.session_id:
            checks_passed.append("session_id_present")
        else:
            checks_failed.append("session_id_present")
            proposed_verdict = GateVerdict.REJECTED

        # --- Invariant: agent_id must be non-empty ---
        if ctx.agent_id:
            checks_passed.append("agent_id_present")
        else:
            checks_failed.append("agent_id_present")
            proposed_verdict = GateVerdict.REJECTED

        # --- Circuit breaker ---
        triggered = (
            proposed_verdict == GateVerdict.REJECTED
            and ctx.consecutive_rejections + 1 >= self.CIRCUIT_BREAKER_THRESHOLD
        )

        if triggered:
            proposed_verdict = GateVerdict.ESCALATED

        return GateResult(
            verdict=proposed_verdict,
            gate=ctx.gate,
            rationale=(
                f"circuit_breaker_triggered after {self.CIRCUIT_BREAKER_THRESHOLD} rejections"
                if triggered
                else f"{len(checks_failed)} invariant(s) failed"
                if checks_failed
                else "all invariants passed"
            ),
            triggered_circuit_breaker=triggered,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
