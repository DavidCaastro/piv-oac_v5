"""tests/integration/conftest.py — Shared fixtures for integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sdk.core.dag import DAG, DAGBuilder, DAGNode
from sdk.providers.base import ProviderResponse


def make_stub_dag(node_count: int = 1) -> DAG:
    """Build a minimal DAG with `node_count` nodes for testing."""
    builder = DAGBuilder()
    for i in range(node_count):
        builder.add(DAGNode(
            node_id=f"node_{i}",
            domain="test",
            description=f"Test node {i}",
            experts=1,
        ))
    return builder.build()


def mock_provider_response(content: str) -> ProviderResponse:
    """Build a ProviderResponse stub with the given content."""
    return ProviderResponse(
        content=content,
        model="test-model",
        input_tokens=10,
        output_tokens=20,
        raw=None,
    )


def make_mock_session(session_id: str = "test-session-0000") -> MagicMock:
    """Build a minimal AsyncSession mock for testing individual phase methods."""
    session = MagicMock()
    session._session_id = session_id
    return session


@pytest.fixture
def stub_dag_single():
    return make_stub_dag(1)


@pytest.fixture
def stub_dag_multi():
    return make_stub_dag(3)
