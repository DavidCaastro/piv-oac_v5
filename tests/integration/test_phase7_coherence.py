"""tests/integration/test_phase7_coherence.py — Integration tests for PHASE 7 CoherenceAgent gate.

Verifies single-node advisory vs multi-node blocking behaviour.
Uses AsyncMock providers — no real LLM calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sdk.core.session_async import ExpertResult

from .conftest import make_stub_dag, mock_provider_response

pytestmark = pytest.mark.integration


@pytest.fixture
def async_session_coh(tmp_path):
    """AsyncSession stub for coherence gate testing."""
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
    return session


def _setup_loader_coh(session):
    agent_cfg = MagicMock()
    agent_cfg.agent_md = "coherence agent"
    agent_cfg.contract_md = "contract"
    agent_cfg.base_md = "base"
    skill_cfg = MagicMock()
    skill_cfg.content = "rubric"
    session._loader.load_agent.return_value = agent_cfg
    session._loader.load_skill.return_value = skill_cfg


def _make_expert(node_id: str, success: bool = True) -> ExpertResult:
    return ExpertResult(
        expert_id=f"SpecialistAgent-abc123-{node_id}",
        node_id=node_id,
        success=success,
        content="Output content for " + node_id if success else "",
        tokens_used=100,
        duration_ms=300,
    )


@pytest.mark.asyncio
async def test_single_node_advisory_rejected_does_not_block(async_session_coh):
    """REJECTED on single-node DAG → advisory, pipeline continues (eff_approved=True)."""
    _setup_loader_coh(async_session_coh)
    dag = make_stub_dag(1)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(
        return_value=mock_provider_response("GATE_VERDICT: REJECTED — minor inconsistency")
    )
    async_session_coh._router.get_provider.return_value = mock_provider
    async_session_coh._router.resolve_tier.return_value = MagicMock(value=3)

    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        eff_approved, rationale = await async_session_coh._run_coherence_gate(
            "test-sess-coh0",
            [_make_expert("node_0")],
            "test objective",
            dag,
            [],
        )

    assert eff_approved is True  # single-node → advisory
    assert "inconsistency" in rationale


@pytest.mark.asyncio
async def test_multi_node_blocking_rejected_blocks(async_session_coh):
    """REJECTED on multi-node DAG → blocking (eff_approved=False)."""
    _setup_loader_coh(async_session_coh)
    dag = make_stub_dag(3)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(
        return_value=mock_provider_response("GATE_VERDICT: REJECTED — naming collision")
    )
    async_session_coh._router.get_provider.return_value = mock_provider
    async_session_coh._router.resolve_tier.return_value = MagicMock(value=3)

    experts = [_make_expert(f"node_{i}") for i in range(3)]
    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        eff_approved, rationale = await async_session_coh._run_coherence_gate(
            "test-sess-coh1",
            experts,
            "test objective",
            dag,
            [],
        )

    assert eff_approved is False  # multi-node → blocking
    assert "collision" in rationale


@pytest.mark.asyncio
async def test_no_successful_experts_skips_coherence(async_session_coh):
    """No successful experts → gate skipped with reason 'no_successful_experts'."""
    dag = make_stub_dag(2)
    failed_experts = [_make_expert("node_0", success=False), _make_expert("node_1", success=False)]

    eff_approved, rationale = await async_session_coh._run_coherence_gate(
        "test-sess-coh2",
        failed_experts,
        "test objective",
        dag,
        [],
    )

    assert eff_approved is True
    assert "no experts" in rationale.lower() or "evaluate" in rationale.lower()
