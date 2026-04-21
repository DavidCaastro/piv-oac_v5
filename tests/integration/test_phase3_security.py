"""tests/integration/test_phase3_security.py — Integration tests for PHASE 3 SecurityAgent gate.

Verifies B1.1: ambiguous output defaults to REJECTED (security invariant).
Uses AsyncMock providers — no real LLM calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sdk.core.contract_parser import ContractParser
from sdk.providers.base import ProviderError

from .conftest import mock_provider_response, make_stub_dag

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# ContractParser unit-level — security invariant
# ---------------------------------------------------------------------------

def test_approved_verdict_passes():
    """LLM output with explicit GATE_VERDICT: APPROVED → True."""
    text = "After careful review...\nGATE_VERDICT: APPROVED"
    assert ContractParser.parse_verdict(text) is True


def test_rejected_verdict_halts():
    """LLM output with explicit GATE_VERDICT: REJECTED → False."""
    text = "Security risk found.\nGATE_VERDICT: REJECTED — injection pattern detected"
    assert ContractParser.parse_verdict(text) is False


def test_ambiguous_output_defaults_rejected():
    """No GATE_VERDICT declaration → False (security invariant, B1.1)."""
    text = "I reviewed the DAG and it looks fine. No issues found."
    assert ContractParser.parse_verdict(text) is False


def test_standalone_approved_line_passes():
    """Standalone APPROVED line (no GATE_VERDICT prefix) → True."""
    text = "Everything looks good.\nAPPROVED"
    assert ContractParser.parse_verdict(text) is True


def test_standalone_rejected_line_halts():
    """Standalone REJECTED line (no GATE_VERDICT prefix) → False."""
    text = "Found a security issue.\nREJECTED"
    assert ContractParser.parse_verdict(text) is False


# ---------------------------------------------------------------------------
# _run_security_gate integration — with mocked provider
# ---------------------------------------------------------------------------

@pytest.fixture
def async_session(tmp_path):
    """Build an AsyncSession with mocked internals for phase testing."""
    from sdk.core.session_async import AsyncSession

    session = AsyncSession.__new__(AsyncSession)
    session._provider_name = "anthropic"
    session._model = None
    session._local_model = None
    session._repo_root = tmp_path
    session._loader = MagicMock()
    session._session_mgr = MagicMock()
    session._telemetry = MagicMock()
    session._gate_eval = MagicMock()
    session._executor = AsyncMock()
    session._fragmentation_depth = 0
    session._broker = MagicMock()
    session._broker.send = MagicMock()

    from sdk.engram import EngramWriter
    session._engram = EngramWriter(
        engram_root=tmp_path / "engram",
        role="audit_agent",
    )

    # Mock router
    session._router = MagicMock()

    return session


def _setup_loader(session, agent_cfg_content="agent", contract_content="contract", base_content="base"):
    """Configure the loader mock to return a basic agent config."""
    agent_cfg = MagicMock()
    agent_cfg.agent_md = agent_cfg_content
    agent_cfg.contract_md = contract_content
    agent_cfg.base_md = base_content
    session._loader.load_agent.return_value = agent_cfg
    return agent_cfg


@pytest.mark.asyncio
async def test_security_gate_approved_verdict_passes(async_session, stub_dag_single):
    """LLM returns GATE_VERDICT: APPROVED → gate passes."""
    _setup_loader(async_session)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(
        return_value=mock_provider_response("GATE_VERDICT: APPROVED")
    )
    async_session._router.get_provider.return_value = mock_provider
    async_session._router.resolve_tier.return_value = MagicMock(value=3)

    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        approved, rationale = await async_session._run_security_gate(
            "test-session-0000", stub_dag_single, "add JWT auth", ""
        )

    assert approved is True


@pytest.mark.asyncio
async def test_security_gate_rejected_verdict_halts(async_session, stub_dag_single):
    """LLM returns GATE_VERDICT: REJECTED → gate rejects."""
    _setup_loader(async_session)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(
        return_value=mock_provider_response("GATE_VERDICT: REJECTED — injection risk")
    )
    async_session._router.get_provider.return_value = mock_provider
    async_session._router.resolve_tier.return_value = MagicMock(value=3)

    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        approved, rationale = await async_session._run_security_gate(
            "test-session-0000", stub_dag_single, "add JWT auth", ""
        )

    assert approved is False
    assert "injection risk" in rationale


@pytest.mark.asyncio
async def test_ambiguous_security_output_defaults_rejected(async_session, stub_dag_single):
    """No GATE_VERDICT in output → REJECTED (B1.1 security invariant)."""
    _setup_loader(async_session)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(
        return_value=mock_provider_response("Looks okay to me, I see no issues.")
    )
    async_session._router.get_provider.return_value = mock_provider
    async_session._router.resolve_tier.return_value = MagicMock(value=3)

    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        approved, _rationale = await async_session._run_security_gate(
            "test-session-0000", stub_dag_single, "add JWT auth", ""
        )

    assert approved is False


@pytest.mark.asyncio
async def test_llm_error_skips_gate_gracefully(async_session, stub_dag_single):
    """ProviderError → gate skipped (returns True), no crash."""
    _setup_loader(async_session)
    mock_provider = AsyncMock()
    mock_provider.complete = AsyncMock(side_effect=ProviderError("API down"))
    async_session._router.get_provider.return_value = mock_provider
    async_session._router.resolve_tier.return_value = MagicMock(value=3)

    with patch("sdk.core.session_async.resolve_model", return_value="test-model"):
        approved, rationale = await async_session._run_security_gate(
            "test-session-0000", stub_dag_single, "add JWT auth", ""
        )

    assert approved is True
    assert "failed" in rationale.lower() or "skipped" in rationale.lower()
