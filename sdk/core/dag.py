"""sdk/core/dag.py — DAGBuilder, DAGNode, SpecDAGParser (Tier 1, deterministic, no LLM).

SpecDAGParser reads specs/active/functional.md and extracts task blocks marked with:
    ### task::<node_id>
    - **domain**: <value>
    - **description**: <value>
    - **depends_on**: <node_id,...> or (none)
    - **files_in_scope**: <path,...> or (tbd)
    - **experts**: <int>

If no functional.md exists or it contains no task blocks, parse() returns None
so the caller can fall back to a stub DAG. Never raises on missing file.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


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

    def add(self, node: DAGNode) -> DAGBuilder:
        if node.node_id in self._nodes:
            raise DAGValidationError(f"Duplicate node_id: '{node.node_id}'")
        self._nodes[node.node_id] = node
        return self

    def build(self) -> DAG:
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


# ---------------------------------------------------------------------------
# SpecDAGParser — Tier 1 parser for specs/active/functional.md task blocks
# ---------------------------------------------------------------------------

# Matches:  ### task::some-node-id
_TASK_HEADING = re.compile(r"^###\s+task::([A-Za-z0-9_\-\.]+)\s*$", re.MULTILINE)

# Matches:  - **key**: value
_FIELD_LINE = re.compile(r"^\s*-\s+\*\*([a-z_]+)\*\*\s*:\s*(.+)$")


class SpecDAGParser:
    """Parse task blocks from specs/active/functional.md into a DAG.

    Reads the functional spec produced by SpecWriter (PHASE 0.2).
    Returns None when no spec or no task blocks are found — callers must
    fall back to a stub DAG in that case.

    All parsing is Tier 1 (regex, no LLM). Invalid or malformed task
    blocks are logged and skipped; valid ones are assembled via DAGBuilder.
    """

    def __init__(self, specs_root: Path) -> None:
        self._specs_root = specs_root

    def parse(self) -> DAG | None:
        """Parse specs/active/functional.md and return a validated DAG.

        Returns:
            DAG if ≥1 valid task blocks found, None otherwise.
        """
        functional_md = self._specs_root / "active" / "functional.md"
        if not functional_md.exists():
            logger.debug("[SpecDAGParser] specs/active/functional.md not found — stub DAG needed")
            return None

        text = functional_md.read_text(encoding="utf-8")
        nodes = self._extract_nodes(text)

        if not nodes:
            logger.warning("[SpecDAGParser] No task blocks found in functional.md — stub DAG needed")
            return None

        builder = DAGBuilder()
        for node in nodes:
            try:
                builder.add(node)
            except DAGValidationError as exc:
                logger.error("[SpecDAGParser] Skipping node '%s': %s", node.node_id, exc)

        try:
            dag = builder.build()
            logger.info("[SpecDAGParser] DAG built: %d node(s)", len(dag.nodes))
            return dag
        except DAGValidationError as exc:
            logger.error("[SpecDAGParser] DAG validation failed: %s — falling back to stub", exc)
            return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _extract_nodes(self, text: str) -> list[DAGNode]:
        """Extract all task blocks from the markdown text."""
        # Split on task headings to get per-task chunks
        parts = _TASK_HEADING.split(text)
        # parts = [preamble, node_id_1, body_1, node_id_2, body_2, ...]
        nodes: list[DAGNode] = []

        # Iterate pairs: (node_id, body)
        for i in range(1, len(parts), 2):
            node_id = parts[i].strip()
            body    = parts[i + 1] if i + 1 < len(parts) else ""
            node    = self._parse_block(node_id, body)
            if node is not None:
                nodes.append(node)

        return nodes

    def _parse_block(self, node_id: str, body: str) -> DAGNode | None:
        """Parse a single task block body into a DAGNode."""
        fields: dict[str, str] = {}
        for line in body.splitlines():
            m = _FIELD_LINE.match(line)
            if m:
                fields[m.group(1)] = m.group(2).strip()

        # Require at minimum domain + description
        if "domain" not in fields or "description" not in fields:
            logger.warning(
                "[SpecDAGParser] task::%s missing 'domain' or 'description' — skipped",
                node_id,
            )
            return None

        depends_raw = fields.get("depends_on", "(none)")
        dependencies = (
            []
            if depends_raw.lower() in ("(none)", "none", "")
            else [d.strip() for d in depends_raw.split(",") if d.strip()]
        )

        files_raw = fields.get("files_in_scope", "(tbd)")
        files_in_scope = (
            []
            if files_raw.lower() in ("(tbd)", "tbd", "")
            else [f.strip() for f in files_raw.split(",") if f.strip()]
        )

        experts_raw = fields.get("experts", "1")
        try:
            experts = max(1, int(experts_raw))
        except ValueError:
            experts = 1

        return DAGNode(
            node_id=node_id,
            domain=fields["domain"],
            description=fields["description"],
            dependencies=dependencies,
            experts=experts,
            files_in_scope=files_in_scope,
        )
