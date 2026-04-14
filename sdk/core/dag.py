"""sdk/core/dag.py — DAGBuilder and DAGNode (Tier 1, deterministic, no LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class NodeStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    BLOCKED   = "blocked"  # dependencies not yet completed


@dataclass
class DAGNode:
    """A single node in the execution DAG.

    Attributes:
        node_id:      Unique identifier (e.g. "auth.jwt-service").
        domain:       Domain label (e.g. "auth", "payments").
        description:  Human-readable task description.
        dependencies: node_id values this node depends on.
        experts:      Number of Specialist Agents required (1–N).
        status:       Current execution status.
        files_in_scope: Declared output file paths (no overlap enforced here).
    """

    node_id: str
    domain: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    experts: int = 1
    status: NodeStatus = NodeStatus.PENDING
    files_in_scope: list[str] = field(default_factory=list)

    def is_ready(self, completed_ids: set[str]) -> bool:
        """Return True if all dependencies have been completed."""
        return all(dep in completed_ids for dep in self.dependencies)


class DAGValidationError(Exception):
    """Raised when the DAG contains cycles or duplicate node IDs."""


class DAGBuilder:
    """Build and validate a directed acyclic graph of domain tasks.

    Input: a list of DAGNode instances (spec-derived, never LLM-generated at runtime).
    Output: a validated DAG with topological ordering.

    Invariants:
    - No duplicate node_ids
    - No cycles
    - Every dependency references a declared node
    - No two nodes share files_in_scope entries (enforced during plan review, warned here)
    """

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}

    def add(self, node: DAGNode) -> "DAGBuilder":
        if node.node_id in self._nodes:
            raise DAGValidationError(f"Duplicate node_id: '{node.node_id}'")
        self._nodes[node.node_id] = node
        return self

    def build(self) -> "DAG":
        """Validate and return the finalized DAG."""
        self._validate_references()
        order = self._topological_sort()
        self._warn_file_overlap()
        return DAG(nodes=self._nodes, topological_order=order)

    def _validate_references(self) -> None:
        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    raise DAGValidationError(
                        f"Node '{node.node_id}' depends on unknown node '{dep}'"
                    )

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm — raises DAGValidationError on cycle detection."""
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for node in self._nodes.values():
            for dep in node.dependencies:
                in_degree[node.node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for candidate in self._nodes.values():
                if nid in candidate.dependencies:
                    in_degree[candidate.node_id] -= 1
                    if in_degree[candidate.node_id] == 0:
                        queue.append(candidate.node_id)

        if len(order) != len(self._nodes):
            raise DAGValidationError("DAG contains a cycle — cannot build execution order")

        return order

    def _warn_file_overlap(self) -> None:
        seen: dict[str, str] = {}
        for node in self._nodes.values():
            for f in node.files_in_scope:
                if f in seen:
                    # Warn only — enforcement is Gate 2's responsibility
                    import warnings
                    warnings.warn(
                        f"File '{f}' declared in both '{seen[f]}' and '{node.node_id}' — "
                        "overlap will be rejected at Gate 2",
                        stacklevel=2,
                    )
                else:
                    seen[f] = node.node_id


@dataclass
class DAG:
    """Finalized, validated execution DAG."""

    nodes: dict[str, DAGNode]
    topological_order: list[str]

    def ready_nodes(self, completed_ids: set[str]) -> list[DAGNode]:
        """Return nodes that are PENDING and have all dependencies completed."""
        return [
            self.nodes[nid]
            for nid in self.topological_order
            if self.nodes[nid].status == NodeStatus.PENDING
            and self.nodes[nid].is_ready(completed_ids)
        ]

    def mark_completed(self, node_id: str) -> None:
        self.nodes[node_id].status = NodeStatus.COMPLETED

    def mark_failed(self, node_id: str) -> None:
        self.nodes[node_id].status = NodeStatus.FAILED

    def __iter__(self) -> Iterator[DAGNode]:
        return (self.nodes[nid] for nid in self.topological_order)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for .piv/ session state."""
        return {
            "topological_order": self.topological_order,
            "nodes": {
                nid: {
                    "domain": n.domain,
                    "description": n.description,
                    "dependencies": n.dependencies,
                    "experts": n.experts,
                    "status": n.status,
                    "files_in_scope": n.files_in_scope,
                }
                for nid, n in self.nodes.items()
            },
        }
