"""Unit tests for sdk/core/dag.py — DAGBuilder and DAG."""

import pytest

from sdk.core.dag import DAGBuilder, DAGNode, DAGValidationError, NodeStatus


@pytest.mark.unit
class TestDAGBuilder:

    def test_simple_linear_dag(self):
        dag = (
            DAGBuilder()
            .add(DAGNode("a", "domain", "Node A"))
            .add(DAGNode("b", "domain", "Node B", dependencies=["a"]))
            .build()
        )
        assert dag.topological_order == ["a", "b"]

    def test_parallel_nodes(self):
        dag = (
            DAGBuilder()
            .add(DAGNode("x", "domain", "Node X"))
            .add(DAGNode("y", "domain", "Node Y"))
            .build()
        )
        assert set(dag.topological_order) == {"x", "y"}

    def test_cycle_raises_error(self):
        with pytest.raises(DAGValidationError, match="cycle"):
            (
                DAGBuilder()
                .add(DAGNode("a", "domain", "A", dependencies=["b"]))
                .add(DAGNode("b", "domain", "B", dependencies=["a"]))
                .build()
            )

    def test_duplicate_node_id_raises_error(self):
        with pytest.raises(DAGValidationError, match="Duplicate"):
            (
                DAGBuilder()
                .add(DAGNode("a", "domain", "First"))
                .add(DAGNode("a", "domain", "Second"))
                .build()
            )

    def test_missing_dependency_raises_error(self):
        with pytest.raises(DAGValidationError, match="unknown"):
            (
                DAGBuilder()
                .add(DAGNode("a", "domain", "A", dependencies=["nonexistent"]))
                .build()
            )

    def test_ready_nodes_respects_dependencies(self):
        dag = (
            DAGBuilder()
            .add(DAGNode("a", "domain", "A"))
            .add(DAGNode("b", "domain", "B", dependencies=["a"]))
            .build()
        )
        ready = dag.ready_nodes(completed_ids=set())
        assert [n.node_id for n in ready] == ["a"]

        dag.mark_completed("a")
        ready = dag.ready_nodes(completed_ids={"a"})
        assert [n.node_id for n in ready] == ["b"]

    def test_to_dict_is_json_serializable(self):
        import json

        dag = DAGBuilder().add(DAGNode("a", "domain", "A")).build()
        data = dag.to_dict()
        json.dumps(data)  # must not raise
