"""tests/integration/test_phase6_evaluation.py — Integration tests for PHASE 6 EvaluationAgent.

Verifies Task 41 fix: JSON without fence fallback in ContractParser.parse_eval_scores.
Uses AsyncMock providers — no real LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdk.core.contract_parser import ContractParser, EvalScoreResult
from sdk.exceptions import MalformedOutput

pytestmark = pytest.mark.integration

_VALID_SCORES = {"FUNC": 0.9, "SEC": 0.8, "QUAL": 0.7, "COH": 0.6, "FOOT": 0.5}
_EXPECTED_AGGREGATE = round(
    0.9 * 0.35 + 0.8 * 0.25 + 0.7 * 0.20 + 0.6 * 0.15 + 0.5 * 0.05, 3
)


def _json_payload(**extra) -> dict:
    return {
        "expert_id": "SpecialistAgent-abc123-node_0",
        "scores": _VALID_SCORES,
        "aggregate": _EXPECTED_AGGREGATE,
        "rationale": "Good output",
        **extra,
    }


# ---------------------------------------------------------------------------
# ContractParser.parse_eval_scores unit-level
# ---------------------------------------------------------------------------

def test_json_fence_parsed_correctly():
    """Output with ```json``` fence → scores extracted correctly."""
    text = f"Here are my scores:\n```json\n{json.dumps(_json_payload())}\n```"
    result = ContractParser.parse_eval_scores(text, "exp-1", "sess-1")
    assert isinstance(result, EvalScoreResult)
    assert result.parse_error is False
    assert result.aggregate == _EXPECTED_AGGREGATE
    assert result.scores == _VALID_SCORES


def test_json_without_fence_fallback():
    """JSON without fence block → fallback regex extracts scores (Task 41 fix)."""
    payload = json.dumps(_json_payload())
    text = f"Evaluation results: {payload}"
    result = ContractParser.parse_eval_scores(text, "exp-1", "sess-1")
    assert isinstance(result, EvalScoreResult)
    assert result.parse_error is False
    assert result.aggregate == _EXPECTED_AGGREGATE


def test_malformed_json_in_fence_raises():
    """Fence block with syntactically invalid JSON (but regex matches) → MalformedOutput raised."""
    # Use valid braces so the regex matches, but invalid JSON inside
    text = '```json\n{"scores": {invalid: value}}\n```'
    with pytest.raises(MalformedOutput) as exc_info:
        ContractParser.parse_eval_scores(text, "exp-1", "sess-1")
    assert "exp-1" in str(exc_info.value)


def test_malformed_json_returns_parse_error():
    """No JSON at all → EvalScoreResult with parse_error=True, aggregate=0.0."""
    text = "I could not evaluate this output properly."
    result = ContractParser.parse_eval_scores(text, "exp-1", "sess-1")
    assert result.parse_error is True
    assert result.aggregate == 0.0
    assert result.scores == {}


def test_eval_score_result_to_dict():
    """EvalScoreResult.to_dict() returns expected keys."""
    result = EvalScoreResult(
        session_id="s1",
        expert_id="e1",
        phase="PHASE_6",
        scores=_VALID_SCORES,
        aggregate=_EXPECTED_AGGREGATE,
    )
    d = result.to_dict()
    assert d["session_id"] == "s1"
    assert d["expert_id"] == "e1"
    assert d["aggregate"] == _EXPECTED_AGGREGATE
    assert "timestamp_ms" in d
    assert d["parse_error"] is False


# ---------------------------------------------------------------------------
# _run_evaluation integration — engram write verification
# ---------------------------------------------------------------------------

@pytest.fixture
def async_session_eval(tmp_path):
    """AsyncSession stub for evaluation phase testing."""
    from sdk.core.session_async import AsyncSession

    session = AsyncSession.__new__(AsyncSession)
    session._provider_name = "anthropic"
    session._model = None
    session._local_model = None
    session._repo_root = tmp_path
    session._loader = MagicMock()
    session._session_mgr = MagicMock()
    session._telemetry = MagicMock()
    session._broker = MagicMock()
    session._broker.send = MagicMock()
    session._router = MagicMock()

    from sdk.engram import EngramWriter
    session._engram = EngramWriter(
        engram_root=tmp_path / "engram",
        role="audit_agent",
    )
    return session, tmp_path


@pytest.mark.asyncio
async def test_scores_written_to_engram(async_session_eval):
    """Scores are written to engram/metrics/logs_scores/<session_id>.jsonl."""
    from unittest.mock import AsyncMock, patch
    from sdk.core.session_async import ExpertResult

    session, tmp_path = async_session_eval

    agent_cfg = MagicMock()
    agent_cfg.agent_md = "eval agent"
    agent_cfg.contract_md = "contract"
    agent_cfg.base_md = "base"
    skill_cfg = MagicMock()
    skill_cfg.content = "rubric"
    session._loader.load_agent.return_value = agent_cfg
    session._loader.load_skill.return_value = skill_cfg

    json_output = f"```json\n{json.dumps(_json_payload())}\n```"
    mock_provider = AsyncMock()
    from sdk.providers.base import ProviderResponse
    mock_provider.complete = AsyncMock(
        return_value=ProviderResponse(
            content=json_output,
            model="test-model",
            input_tokens=5,
            output_tokens=10,
            raw=None,
        )
    )
    session._router.get_provider.return_value = mock_provider
    session._router.resolve_tier.return_value = MagicMock(value=3)

    expert_results = [
        ExpertResult(
            expert_id="SpecialistAgent-abc123-node_0",
            node_id="node_0",
            success=True,
            content="Implementation complete.",
            tokens_used=100,
            duration_ms=500,
        )
    ]

    session_id = "test-sess-eval0"
    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        scores = await session._run_evaluation(session_id, expert_results, "test objective")

    assert len(scores) == 1
    engram_path = tmp_path / "engram" / "metrics" / "logs_scores" / f"{session_id}.jsonl"
    assert engram_path.exists()
    content = engram_path.read_text()
    assert "SpecialistAgent" in content
