# skills/dag-design.md — DAG Design

## When to Load

When MasterOrchestrator builds the execution DAG from confirmed specs.

## DAG Invariants

- Built ONLY from confirmed specs (never from raw objective)
- Topologically sorted (Kahn's algorithm, deterministic)
- No duplicate node_ids
- No file overlap between nodes (two nodes never write to the same file)
- No cycles

## Node Design Rules

| Rule | Detail |
|---|---|
| Atomic scope | One coherent responsibility per node (one class, one module, one endpoint) |
| No overlap | Two nodes never write to the same file |
| Spec-grounded | Each node maps to a distinct section of functional.md |
| Size guideline | ≤ 400 lines of new/modified code per expert per node |

## Example DAG

```python
from sdk.core.dag import DAGBuilder, DAGNode

dag = (
    DAGBuilder()
    .add(DAGNode("auth.models",   "auth", "User + Token models",    experts=1, files_in_scope=["app/models/user.py"]))
    .add(DAGNode("auth.service",  "auth", "JWT service logic",      experts=1, files_in_scope=["app/services/auth.py"], dependencies=["auth.models"]))
    .add(DAGNode("auth.endpoints","auth", "REST endpoints for auth",experts=1, files_in_scope=["app/routers/auth.py"],  dependencies=["auth.service"]))
    .build()
)
```

## Parallel Execution

Nodes with no shared dependencies execute in parallel (different DomainOrchestrators).
DAG ready_nodes() returns all nodes whose dependencies are completed.

## Split Guideline

If a node would require > 400 lines: split into two nodes with a dependency edge.
Splitting is the DomainOrchestrator's responsibility, not the Specialist Agent's.

## DAG Serialization

DAG is stored in `.piv/active/<session_id>.json` under the `dag` key.
`DAG.to_dict()` produces JSON-compatible output.
