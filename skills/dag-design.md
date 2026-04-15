# skills/dag-design.md — DAG Design

## When to Load

When MasterOrchestrator builds the execution DAG from confirmed specs.

---

## DAG Invariants

- (A) Built ONLY from confirmed specs (never from raw objective)
- (B) Topologically sorted (Kahn's algorithm, deterministic)
- (C) No duplicate node_ids
- (D) No two nodes may claim the same file unless one depends on the other (write-exclusivity rule)
- (E) Each node's domain must match an available ExpertAgent domain registered in the session
- (F) `depends_on` must form a DAG — Kahn's algorithm verifies acyclicity before execution begins; a cycle detected at build time causes an immediate `SpecValidationError`

---

## Node Design Rules

| Rule | Detail |
|---|---|
| Atomic scope | One coherent responsibility per node (one class, one module, one endpoint) |
| No overlap | Two nodes never write to the same file (Invariant D) |
| Spec-grounded | Each node maps to a distinct section of functional.md |
| Size guideline | Target 200–400 lines of new/modified code per node per expert |
| Upper bound | Nodes estimated > 400 lines of change must be split (see Split Guideline) |

---

## Topological Sort Verification

Kahn's algorithm is applied by `SpecDAGParser` at DAG build time. Steps:

```
(1) Compute in-degree for all nodes:
        in_degree[node] = number of nodes that node depends on

(2) Initialize queue:
        queue = [node for node in all_nodes if in_degree[node] == 0]
        (these are root nodes — no dependencies)

(3) Process queue (iteratively):
        while queue is not empty:
            node = queue.pop(0)
            processed_count += 1
            current_batch.append(node)
            for each dependent of node:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
            if queue is empty and processed_count < total_nodes:
                → a cycle exists — stop processing

(4) Cycle detection:
        if processed_count < total_nodes:
            raise CyclicDependencyError(
                f"Cycle detected: {total_nodes - processed_count} nodes unreachable"
            )
            → spec is rejected, no execution begins
```

The output of Kahn's is an ordered list of batches (see Parallel Execution Batches).

---

## Parallel Execution Batches

Kahn's algorithm naturally produces batches. A **batch** is the set of nodes that have
zero in-degree at each step of the algorithm. All nodes in the same batch have their
dependencies already completed and can execute concurrently via `asyncio.gather()`.

### Example: 4-node DAG

Nodes and dependencies:

```
auth-models       (no deps)
auth-service      depends_on: auth-models
auth-endpoints    depends_on: auth-service
auth-tests        depends_on: auth-models       ← parallel with auth-service
```

Kahn's batch decomposition:

```
Batch 0 (in-degree=0):  [auth-models]
    → execute auth-models → mark complete → reduce in-degree of dependents

Batch 1 (in-degree=0 after batch 0):  [auth-service, auth-tests]
    → asyncio.gather(auth-service, auth-tests)  ← parallel execution
    → both complete → reduce in-degree of auth-endpoints

Batch 2 (in-degree=0 after batch 1):  [auth-endpoints]
    → execute auth-endpoints
```

Total wall-clock time = time(batch 0) + time(batch 1) + time(batch 2)
instead of sum of all 4 nodes sequentially.

---

## Split Guideline (400-line threshold)

When a node is estimated to require > 400 lines of new/modified code:

### Split Strategy A — Vertical split (by feature area)

- Identify distinct feature areas within the node's scope.
- Each area becomes an independent node with its own `files_in_scope`.
- Nodes at the same level may be parallel if they share no files.
- Use when: the node covers multiple independent sub-features.

### Split Strategy B — Horizontal split (by layer)

- Original node splits into: interface node → implementation node → tests node.
- Each depends on the previous (sequential chain).
- Use when: the node has a single feature but significant layered depth.

### After split

- The original oversized node becomes a **meta-node**: no `files_in_scope`, no expert work.
- Meta-node exists only to group sub-nodes under a logical name in the DAG.
- Sub-nodes list the meta-node in `depends_on` only if sequencing requires it.
- Maximum 6 sub-nodes per split (SecurityAgent contract limit).

---

## Node Complexity Estimation

How to estimate node size before DAG execution begins:

| Signal | Estimation rule |
|---|---|
| `files_in_scope` count | Each file ≈ 50 tokens/line average; multiply by expected change % |
| `description` word count | > 100 words in description → likely > 200 lines of change |
| `domain = "testing"` | Testing nodes typically 0.5× the size of their paired implementation node |
| `experts` count | Higher expert count indicates orchestrator expects parallel subtasks within node |

These are heuristics used at DAG build time to flag candidates for splitting before
any LLM call is made. Actual line counts are verified post-execution.

---

## Example DAG (4 nodes)

```python
from sdk.core.dag import DAGBuilder, DAGNode

dag = (
    DAGBuilder()
    .add(DAGNode(
        "auth-models",
        domain="auth",
        description="User + Token models",
        experts=1,
        files_in_scope=["app/models/user.py"],
    ))
    .add(DAGNode(
        "auth-service",
        domain="auth",
        description="JWT service logic",
        experts=1,
        files_in_scope=["app/services/auth.py"],
        dependencies=["auth-models"],
    ))
    .add(DAGNode(
        "auth-tests",
        domain="testing",
        description="Unit tests for auth models",
        experts=1,
        files_in_scope=["tests/test_auth_models.py"],
        dependencies=["auth-models"],
    ))
    .add(DAGNode(
        "auth-endpoints",
        domain="auth",
        description="REST endpoints for auth",
        experts=1,
        files_in_scope=["app/routers/auth.py"],
        dependencies=["auth-service"],
    ))
    .build()
)
```

Kahn's batches for this DAG:

```
Batch 0: [auth-models]
Batch 1: [auth-service, auth-tests]   ← asyncio.gather()
Batch 2: [auth-endpoints]
```

---

## Serialization

DAG is stored in `.piv/active/<session_id>.json` under the `dag` key.
`DAG.to_dict()` produces JSON-compatible output.

---

## What DAG Design Does NOT Do

- Does not write code — it defines structure only.
- Does not assign LLM models — that is ExpertAgent's responsibility.
- Does not re-order nodes at runtime — batch order is fixed at build time by Kahn's.
- Does not infer domain from description — domain must be explicitly set per node.

<!-- v5.1 — expanded Tier 4 -->
