"""Unit tests for sdk/gates/evaluator.py — GateEvaluator."""

import pytest

from sdk.gates.evaluator import GateContext, GateEvaluator, GateType, GateVerdict


@pytest.mark.unit
class TestGateEvaluator:

    def setup_method(self):
        self.evaluator = GateEvaluator()

    def _ctx(self, consecutive_rejections=0):
        return GateContext(
            gate=GateType.GATE_1,
            session_id="test-session-id",
            agent_id="CoherenceAgent",
            payload={},
            consecutive_rejections=consecutive_rejections,
        )

    def test_approved_verdict_passes(self):
        result = self.evaluator.evaluate(self._ctx(), GateVerdict.APPROVED)
        assert result.verdict == GateVerdict.APPROVED
        assert not result.triggered_circuit_breaker

    def test_rejected_verdict_passes_below_threshold(self):
        result = self.evaluator.evaluate(self._ctx(consecutive_rejections=1), GateVerdict.REJECTED)
        assert result.verdict == GateVerdict.REJECTED
        assert not result.triggered_circuit_breaker

    def test_circuit_breaker_triggers_at_threshold(self):
        ctx = self._ctx(consecutive_rejections=2)  # +1 = 3 → triggers
        result = self.evaluator.evaluate(ctx, GateVerdict.REJECTED)
        assert result.verdict == GateVerdict.ESCALATED
        assert result.triggered_circuit_breaker

    def test_missing_session_id_causes_rejection(self):
        ctx = GateContext(
            gate=GateType.GATE_1,
            session_id="",
            agent_id="CoherenceAgent",
            payload={},
        )
        result = self.evaluator.evaluate(ctx, GateVerdict.APPROVED)
        assert result.verdict == GateVerdict.REJECTED
        assert "session_id_present" in result.checks_failed

    def test_missing_agent_id_causes_rejection(self):
        ctx = GateContext(
            gate=GateType.GATE_2,
            session_id="valid-id",
            agent_id="",
            payload={},
        )
        result = self.evaluator.evaluate(ctx, GateVerdict.APPROVED)
        assert result.verdict == GateVerdict.REJECTED
        assert "agent_id_present" in result.checks_failed
