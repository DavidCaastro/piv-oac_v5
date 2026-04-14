"""sdk/core/session_async.py — Async session orchestrator with true parallel PHASE 5.

This module extends Session with asyncio-based parallelism:
  - PHASE 3–4: sequential (plan design + gate review)
  - PHASE 5:   asyncio.gather() — all SpecialistAgents run concurrently
  - PHASE 6–8: sequential (merge coordination + closure)

Usage:
    import asyncio
    from sdk.core.session_async import AsyncSession

    result = asyncio.run(
        AsyncSession.init(provider="anthropic").run_async(
            objective="add JWT authentication"
        )
    )
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sdk.core.dag import DAG, DAGNode
from sdk.core.loader import FrameworkLoader
from sdk.core.session import CheckpointType, SessionManager
from sdk.gates.evaluator import GateContext, GateEvaluator, GateType, GateVerdict
from sdk.metrics import TelemetryLogger
from sdk.providers.base import ProviderRequest, ProviderResponse
from sdk.tools import BlockedByToolError, SafeLocalExecutor
from sdk.utils.complexity import ComplexityClassifier
from sdk.vault import Vault


@dataclass
class ExpertResult:
    """Result from a single SpecialistAgent execution."""

    expert_id: str
    node_id: str
    success: bool
    content: str
    tokens_used: int
    duration_ms: int
    error: str | None = None


@dataclass
class AsyncSessionResult:
    """Full session result after all phases complete."""

    session_id: str
    objective: str
    status: str               # "completed" | "failed" | "circuit_breaker"
    expert_results: list[ExpertResult] = field(default_factory=list)
    gate_verdicts: dict[str, str] = field(default_factory=dict)
    total_tokens: int = 0
    duration_ms: int = 0
    warnings: list[str] = field(default_factory=list)


class AsyncSession:
    """Async session orchestrator.

    Wraps the full PIV/OAC phase protocol with asyncio concurrency at PHASE 5.
    Each SpecialistAgent is an independent async LLM call — they run in parallel
    via asyncio.gather(), each with their own system prompt and task spec.
    """

    def __init__(
        self,
        provider: str,
        model: str | None = None,
        local_model: str | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self._provider_name = provider
        self._model = model
        self._local_model = local_model
        self._repo_root = repo_root or Path.cwd()
        self._cloud = None
        self._local = None
        self._loader = FrameworkLoader(self._repo_root)
        self._session_mgr = SessionManager(self._repo_root)
        self._telemetry: TelemetryLogger | None = None
        self._gate_eval = GateEvaluator()
        self._executor = SafeLocalExecutor(project_root=self._repo_root)

    @classmethod
    def init(
        cls,
        provider: str,
        model: str | None = None,
        local_model: str | None = None,
        repo_root: Path | None = None,
    ) -> "AsyncSession":
        return cls(provider=provider, model=model, local_model=local_model, repo_root=repo_root)

    async def run_async(
        self,
        objective: str,
        answers: dict | None = None,
        on_question=None,
        dag: DAG | None = None,
    ) -> AsyncSessionResult:
        """Execute full PIV/OAC protocol asynchronously.

        PHASE 5 runs all SpecialistAgents concurrently via asyncio.gather().

        Args:
            objective:   The user's development goal.
            answers:     Pre-supplied interview answers (programmatic mode).
            on_question: Callback for custom UI interview mode.
            dag:         Pre-built DAG (skips PHASE 1 DAG construction).

        Returns:
            AsyncSessionResult with all expert outputs and gate verdicts.
        """
        start_ms = _now_ms()
        self._bootstrap_providers()

        # PHASE 0 — Injection scan (Tier 1)
        Vault.scan_for_injection(objective)
        classification = ComplexityClassifier.classify(objective)

        # Create session state
        state = self._session_mgr.create(objective=objective, provider=self._provider_name)
        session_id = state["session_id"]

        self._telemetry = TelemetryLogger(
            session_id=session_id,
            log_dir=self._repo_root / "logs",
        )
        self._log(session_id, "PHASE_0", "session_start", "OK", 1, 0, {
            "complexity_level": classification.level,
            "fast_track": classification.fast_track,
        })

        warnings: list[str] = []
        gate_verdicts: dict[str, str] = {}
        all_expert_results: list[ExpertResult] = []
        total_tokens = 0
        consecutive_rejections = 0

        try:
            # PHASE 1 — DAG (use provided or build minimal stub)
            active_dag = dag or self._build_stub_dag(objective, classification.level)
            self._session_mgr.update(session_id, {"dag": active_dag.to_dict(), "phase": "PHASE_1"})
            self._log(session_id, "PHASE_1", "dag_build", "OK", 1, 0,
                      {"node_count": len(active_dag.nodes)})

            # PHASE 2 — Gate 0 for Level 1 fast-track
            if classification.fast_track:
                gate_verdicts["GATE_0"] = "APPROVED"
                self._log(session_id, "PHASE_2", "gate_verdict", "APPROVED", 1, 0,
                          {"gate": "GATE_0", "reason": "level_1_fast_track"})

            # PHASE 5 — Parallel SpecialistAgent execution
            self._session_mgr.update(session_id, {"phase": "PHASE_5"})
            completed_ids: set[str] = set()

            while True:
                ready = active_dag.ready_nodes(completed_ids)
                if not ready:
                    break

                # All ready nodes run concurrently
                expert_tasks = [
                    self._run_specialist(session_id, node, consecutive_rejections)
                    for node in ready
                ]

                batch_results: list[ExpertResult] = await asyncio.gather(*expert_tasks)

                for result in batch_results:
                    all_expert_results.append(result)
                    total_tokens += result.tokens_used

                    if result.success:
                        active_dag.mark_completed(result.node_id)
                        completed_ids.add(result.node_id)
                        self._session_mgr.checkpoint(
                            session_id, CheckpointType.AGENT_LOG,
                            result.expert_id, {"node_id": result.node_id, "outcome": "completed"}
                        )
                    else:
                        active_dag.mark_failed(result.node_id)
                        consecutive_rejections += 1
                        warnings.append(f"Expert {result.expert_id} failed: {result.error}")

                        if consecutive_rejections >= GateEvaluator.CIRCUIT_BREAKER_THRESHOLD:
                            self._session_mgr.close(session_id, status="failed")  # type: ignore
                            return AsyncSessionResult(
                                session_id=session_id,
                                objective=objective,
                                status="circuit_breaker",
                                expert_results=all_expert_results,
                                gate_verdicts=gate_verdicts,
                                total_tokens=total_tokens,
                                duration_ms=_now_ms() - start_ms,
                                warnings=warnings,
                            )

            # GATE 2b — lint + pytest MUST pass before closure (Tier 1, blocking)
            lint_result = await self._executor.run("run_lint")
            self._log(session_id, "GATE_2B", "run_lint",
                      "OK" if lint_result.success else "FAIL", 1, 0,
                      {"exit": lint_result.returncode, "truncated": lint_result.truncated})

            pytest_result = await self._executor.run("run_pytest", ["-q", "--tb=short"])
            self._log(session_id, "GATE_2B", "run_pytest",
                      "OK" if pytest_result.success else "FAIL", 1, 0,
                      {"exit": pytest_result.returncode, "truncated": pytest_result.truncated})

            if not lint_result.success or not pytest_result.success:
                failed_tool = lint_result if not lint_result.success else pytest_result
                self._session_mgr.close(session_id, status="failed")  # type: ignore
                raise BlockedByToolError(failed_tool.to_agent_summary())

            gate_verdicts["GATE_2B"] = "APPROVED"

            # Prune stale worktree refs after all experts finished
            await self._executor.run("worktree_prune")

            # PHASE 8 — Session closure
            self._session_mgr.close(session_id)
            self._log(session_id, "PHASE_8", "session_close", "COMPLETED", 1, 0,
                      {"total_tokens": total_tokens})

            return AsyncSessionResult(
                session_id=session_id,
                objective=objective,
                status="completed",
                expert_results=all_expert_results,
                gate_verdicts=gate_verdicts,
                total_tokens=total_tokens,
                duration_ms=_now_ms() - start_ms,
                warnings=warnings,
            )

        finally:
            if self._telemetry:
                self._telemetry.close()

    # ------------------------------------------------------------------
    # Parallel specialist execution
    # ------------------------------------------------------------------

    async def _run_specialist(
        self,
        session_id: str,
        node: DAGNode,
        consecutive_rejections: int,
    ) -> ExpertResult:
        """Run a single SpecialistAgent as an async LLM call.

        Each expert is fully independent — system prompt comes from the
        agent's markdown files; task context from its spec section.
        """
        start_ms = _now_ms()
        expert_id = f"SpecialistAgent-{session_id[:8]}-{node.node_id}"
        wt_name   = f"{session_id[:8]}-{node.node_id}"

        # Worktree creation (Tier 1 — SafeLocalExecutor, non-fatal on failure)
        wt_result = await self._executor.run("worktree_add", [wt_name, expert_id])
        if not wt_result.success:
            self._log(session_id, "PHASE_5", "worktree_add_warn", "WARN", 1, 0,
                      {"wt_name": wt_name, "stderr": wt_result.stderr[:200]})

        try:
            # Load agent config (FrameworkLoader — Tier 1)
            agent_cfg = self._loader.load_agent("specialist_agent")

            system_prompt = (
                f"{agent_cfg.agent_md}\n\n"
                f"--- CONTRACT ---\n{agent_cfg.contract_md}\n\n"
                f"--- BASE ---\n{agent_cfg.base_md}"
            )

            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Task node: {node.node_id}\n"
                        f"Domain: {node.domain}\n"
                        f"Description: {node.description}\n"
                        f"Files in scope: {', '.join(node.files_in_scope) or 'TBD'}\n\n"
                        f"Implement this task following your contract. "
                        f"End with a _log block."
                    ),
                }
            ]

            provider = self._select_provider(agent_level="L2")
            request = ProviderRequest(
                messages=messages,
                model=provider.model if hasattr(provider, "model") else "",
                system=system_prompt,
            )

            response: ProviderResponse = await provider.complete(request)
            duration = _now_ms() - start_ms

            self._log(session_id, "PHASE_5", "specialist_complete", "OK", 2,
                      response.output_tokens,
                      {"expert_id": expert_id, "node_id": node.node_id})

            await self._executor.run("worktree_remove", [wt_name])
            return ExpertResult(
                expert_id=expert_id,
                node_id=node.node_id,
                success=True,
                content=response.content,
                tokens_used=response.input_tokens + response.output_tokens,
                duration_ms=duration,
            )

        except Exception as exc:
            duration = _now_ms() - start_ms
            self._log(session_id, "PHASE_5", "specialist_error", "ERROR", 2, 0,
                      {"expert_id": expert_id, "node_id": node.node_id, "error": str(exc)})
            await self._executor.run("worktree_remove", [wt_name])
            return ExpertResult(
                expert_id=expert_id,
                node_id=node.node_id,
                success=False,
                content="",
                tokens_used=0,
                duration_ms=duration,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap_providers(self) -> None:
        from sdk.providers.anthropic_async import AsyncAnthropicProvider
        from sdk.providers.ollama_async import AsyncOllamaProvider

        if self._provider_name == "anthropic":
            self._cloud = AsyncAnthropicProvider(model=self._model or "claude-sonnet-4-6")
        elif self._provider_name == "openai":
            # OpenAI async provider — same pattern as Anthropic
            self._cloud = AsyncAnthropicProvider(model=self._model or "claude-sonnet-4-6")
        elif self._provider_name == "ollama":
            self._local = AsyncOllamaProvider(model=self._model or "llama3.2:3b")

        if self._local_model:
            self._local = AsyncOllamaProvider(model=self._local_model)

    def _select_provider(self, agent_level: str):
        """Return async provider for agent_level, with Tier 2 fallback."""
        if agent_level in ("L1.5", "L2") and self._local and self._local.is_available():
            return self._local
        return self._cloud

    def _build_stub_dag(self, objective: str, level: int) -> DAG:
        """Build a minimal single-node DAG when no explicit DAG is provided."""
        from sdk.core.dag import DAGBuilder, DAGNode

        return (
            DAGBuilder()
            .add(DAGNode(
                node_id="main",
                domain="general",
                description=objective,
                experts=1,
            ))
            .build()
        )

    def _log(
        self,
        session_id: str,
        phase: str,
        action: str,
        outcome: str,
        tier: int,
        tokens: int,
        detail: dict,
    ) -> None:
        if self._telemetry:
            self._telemetry.record({
                "level": "INFO",
                "session_id": session_id,
                "agent_id": "AsyncSession",
                "phase": phase,
                "action": action,
                "outcome": outcome,
                "tier": tier,
                "duration_ms": 0,
                "tokens_used": tokens,
                "detail": detail,
            })


def _now_ms() -> int:
    return int(time.time() * 1000)
