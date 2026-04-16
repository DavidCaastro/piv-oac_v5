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

from sdk.core.bias_validator import BiasValidationResult, validate_bias_output
from sdk.core.dag import DAG, DAGNode, SpecDAGParser
from sdk.core.model_registry import resolve_model
from sdk.core.interview import (
    CallbackHandler,
    PreSuppliedHandler,
    run_interview,
)
from sdk.core.loader import FrameworkLoader
from sdk.core.session import CheckpointType, SessionManager
from sdk.core.spec_writer import SpecWriter
from sdk.engram import EngramWriter
from sdk.gates.evaluator import GateContext, GateEvaluator, GateType, GateVerdict
from sdk.metrics import TelemetryLogger
from sdk.pmia import (
    GateId,
    PMIABroker,
    PMIAMessage,
    Verdict,
    checkpoint_req,
    escalation,
    gate_verdict,
)
from sdk.pmia.messages import EscalationReason, MessageType
from sdk.providers.base import ProviderRequest, ProviderResponse
from sdk.providers.router import ProviderRouter
from sdk.tools import BlockedByToolError, SafeLocalExecutor
from sdk.utils.complexity import ClassificationResult, ComplexityClassifier
from sdk.vault import Vault

# Complexity level → agent level for provider routing:
#   Level 1 (micro-task)     → L2  — mechanical, can run on local Ollama (Tier 2)
#   Level 2 (architectural)  → L1  — requires genuine reasoning, cloud only (Tier 3)
_COMPLEXITY_TO_AGENT_LEVEL: dict[int, str] = {1: "L2", 2: "L1"}

# Item 38 — SecurityAgent fragmentation depth limit (contracts spec: ≤ 6 sub-agents, depth ≤ 2)
_MAX_FRAGMENTATION_DEPTH = 2


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
        self._gate_eval  = GateEvaluator()
        self._executor   = SafeLocalExecutor(project_root=self._repo_root)
        self._router:  ProviderRouter | None = None   # built after providers bootstrap
        self._broker:  PMIABroker | None = None       # built after telemetry init
        self._fragmentation_depth: int = 0            # item 38: depth counter for CONTEXT_SATURATION
        self._engram   = EngramWriter(
            engram_root=self._repo_root / "engram",
            role="audit_agent",
        )

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
        confirm_specs: bool = False,
    ) -> AsyncSessionResult:
        """Execute full PIV/OAC protocol asynchronously.

        PHASE 5 runs all SpecialistAgents concurrently via asyncio.gather().

        Args:
            objective:     The user's development goal.
            answers:       Pre-supplied interview answers (programmatic mode).
            on_question:   Callback for custom UI interview mode.
            dag:           Pre-built DAG (skips PHASE 1 DAG construction).
            confirm_specs: If True, call handler.confirm() after PHASE 0.2 before
                           building the DAG. User rejection → status="spec_rejected".
                           Requires answers or on_question to be set.

        Returns:
            AsyncSessionResult with all expert outputs and gate verdicts.
        """
        start_ms = _now_ms()
        self._bootstrap_providers()  # also builds self._router

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
        # PMIABroker requires telemetry to be ready (logs every message before processing)
        self._broker = PMIABroker(session_id=session_id, telemetry_logger=self._telemetry)
        # Item 38 — register CONTEXT_SATURATION depth enforcer on the broker
        self._broker.register(MessageType.ESCALATION, self._handle_escalation)

        self._log(session_id, "PHASE_0", "session_start", "OK", 1, 0, {
            "complexity_level": classification.level,
            "fast_track": classification.fast_track,
        })

        # PHASE 0.1 + 0.2 — Interview + SpecWriter (Level 2, when handler available)
        # Skipped for: Level 1 fast-track, caller-provided DAG, no handler supplied.
        if not dag and not classification.fast_track and (answers or on_question):
            handler = (
                PreSuppliedHandler(answers) if answers
                else CallbackHandler(on_question)
            )
            interview_answers = run_interview(objective, handler)
            # Inject session context so template variables are fully resolved
            interview_answers["session_id"] = session_id
            interview_answers["created_at"] = _iso_now()
            self._log(session_id, "PHASE_0_1", "interview_complete", "OK", 1, 0, {
                "keys_collected": list(interview_answers.keys()),
            })

            spec_writer = SpecWriter(self._repo_root / "specs")
            spec_writer.write_functional(interview_answers)
            written = spec_writer.list_written()
            self._log(session_id, "PHASE_0_2", "spec_written", "OK", 1, 0, {
                "files": [str(p) for p in written],
            })

            # Item 39 — spec confirmation gate (PHASE 0.2 → PHASE 1)
            if confirm_specs:
                spec_summary = (
                    f"Specs written to specs/active/ ({len(written)} file(s)). "
                    f"Proceed with DAG construction?"
                )
                if not handler.confirm(spec_summary):
                    self._log(session_id, "PHASE_0_2", "spec_rejected", "ABORTED", 1, 0, {})
                    _result_for_index = AsyncSessionResult(
                        session_id=session_id,
                        objective=objective,
                        status="spec_rejected",
                        duration_ms=_now_ms() - start_ms,
                    )
                    return _result_for_index

        warnings: list[str] = []
        gate_verdicts: dict[str, str] = {}
        all_expert_results: list[ExpertResult] = []
        total_tokens = 0
        consecutive_rejections = 0
        _result_for_index: AsyncSessionResult | None = None  # set at every exit point

        try:
            # PHASE 1 — DAG: provided > spec-parsed > stub (priority order)
            active_dag = (
                dag
                or SpecDAGParser(self._repo_root / "specs").parse()
                or self._build_stub_dag(objective, classification.level)
            )
            self._session_mgr.update(session_id, {"dag": active_dag.to_dict(), "phase": "PHASE_1"})
            self._log(session_id, "PHASE_1", "dag_build", "OK", 1, 0,
                      {"node_count": len(active_dag.nodes)})
            # PMIA: checkpoint after DAG confirmed
            self._broker.send(checkpoint_req(
                agent_id="AsyncSession",
                session_id=session_id,
                phase="PHASE_1",
                state_summary=(
                    f"DAG built: {len(active_dag.nodes)} node(s). "
                    f"Complexity={classification.level} fast_track={classification.fast_track}."
                ),
            ))

            # PHASE 2 — Gate 0 for Level 1 fast-track
            if classification.fast_track:
                gate_verdicts["GATE_0"] = "APPROVED"
                self._log(session_id, "PHASE_2", "gate_verdict", "APPROVED", 1, 0,
                          {"gate": "GATE_0", "reason": "level_1_fast_track"})

            # PHASE 1.5 — BiasAuditAgent (L2 tasks only, Tier 1 validator enforced)
            # Runs AFTER DAG confirmed, BEFORE experts execute.
            # Gate: APPROVED continues to PHASE 5; REJECTED returns early.
            if classification.level == 2 and not classification.fast_track:
                bias_approved, bias_output, bias_missing = await self._run_bias_audit(
                    session_id, active_dag, objective, classification
                )
                gate_verdicts["BIAS_AUDIT"] = "APPROVED" if bias_approved else "REJECTED"
                if not bias_approved:
                    self._broker.send(gate_verdict(
                        agent_id="BiasAuditAgent",
                        session_id=session_id,
                        gate=GateId.GATE_1,
                        verdict=Verdict.REJECTED,
                        rationale="BiasAudit output missing: " + "; ".join(bias_missing),
                    ))
                    self._session_mgr.close(session_id, status="failed")  # type: ignore
                    _result_for_index = AsyncSessionResult(
                        session_id=session_id,
                        objective=objective,
                        status="bias_rejected",
                        gate_verdicts=gate_verdicts,
                        duration_ms=_now_ms() - start_ms,
                        warnings=["BiasAudit REJECTED: " + "; ".join(bias_missing)],
                    )
                    return _result_for_index

            # PHASE 5 — Parallel SpecialistAgent execution
            self._session_mgr.update(session_id, {"phase": "PHASE_5"})
            completed_ids: set[str] = set()

            while True:
                ready = active_dag.ready_nodes(completed_ids)
                if not ready:
                    break

                # All ready nodes run concurrently
                expert_tasks = [
                    self._run_specialist(session_id, node, classification)
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
                    # PMIA: escalate circuit breaker via broker
                    self._broker.send(escalation(
                        agent_id="AsyncSession",
                        session_id=session_id,
                        reason=EscalationReason.UNRESOLVABLE_CONFLICT,
                        context=f"Circuit breaker: {consecutive_rejections} consecutive failures",
                    ))
                    self._session_mgr.close(session_id, status="failed")  # type: ignore
                    _result_for_index = AsyncSessionResult(
                        session_id=session_id,
                        objective=objective,
                        status="circuit_breaker",
                        expert_results=all_expert_results,
                        gate_verdicts=gate_verdicts,
                        total_tokens=total_tokens,
                        duration_ms=_now_ms() - start_ms,
                        warnings=warnings,
                    )
                    return _result_for_index

                # PMIA: checkpoint after each batch (success or partial failure)
                done_count  = len(completed_ids)
                total_nodes = len(active_dag.nodes)
                self._broker.send(checkpoint_req(
                    agent_id="AsyncSession",
                    session_id=session_id,
                    phase="PHASE_5",
                    state_summary=(
                        f"Batch done: {done_count}/{total_nodes} nodes completed. "
                        f"tokens_so_far={total_tokens} failures={consecutive_rejections}."
                    ),
                ))

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
                # PMIA: Gate 2b BLOCKED_BY_TOOL verdict via broker
                self._broker.send(gate_verdict(
                    agent_id="StandardsAgent",
                    session_id=session_id,
                    gate=GateId.GATE_2B,
                    verdict=Verdict.BLOCKED_BY_TOOL,
                    rationale=f"{failed_tool.command} exit={failed_tool.returncode}",
                ))
                self._session_mgr.close(session_id, status="failed")  # type: ignore
                _result_for_index = AsyncSessionResult(
                    session_id=session_id,
                    objective=objective,
                    status="failed",
                    expert_results=all_expert_results,
                    gate_verdicts=gate_verdicts,
                    total_tokens=total_tokens,
                    duration_ms=_now_ms() - start_ms,
                    warnings=warnings + [f"Gate 2b blocked by: {failed_tool.command}"],
                )
                raise BlockedByToolError(failed_tool.to_agent_summary())

            # PMIA: Gate 2b APPROVED verdict via broker
            self._broker.send(gate_verdict(
                agent_id="StandardsAgent",
                session_id=session_id,
                gate=GateId.GATE_2B,
                verdict=Verdict.APPROVED,
                rationale="lint and pytest passed",
            ))
            gate_verdicts["GATE_2B"] = "APPROVED"
            # PMIA: checkpoint — Gate 2b cleared, entering closure
            self._broker.send(checkpoint_req(
                agent_id="AsyncSession",
                session_id=session_id,
                phase="GATE_2B",
                state_summary=(
                    f"Gate 2b APPROVED. lint=OK pytest=OK. "
                    f"total_tokens={total_tokens} experts={len(all_expert_results)}."
                ),
            ))

            # Prune stale worktree refs after all experts finished
            await self._executor.run("worktree_prune")

            # PHASE 8 — Session closure
            # PMIA: final checkpoint before closing (AuditAgent writes to engram/)
            self._broker.send(checkpoint_req(
                agent_id="AsyncSession",
                session_id=session_id,
                phase="PHASE_8",
                state_summary=(
                    f"Session closing: status=completed. "
                    f"experts={len(all_expert_results)} total_tokens={total_tokens} "
                    f"warnings={len(warnings)}."
                ),
            ))
            self._session_mgr.close(session_id)

            # PHASE 8 — AuditAgent writes to engram/ (append-only, atomic)
            self._engram.write_json(
                f"audit/{session_id}/record.json",
                {
                    "objective":      objective[:200],
                    "status":         "completed",
                    "complexity":     classification.level,
                    "fast_track":     classification.fast_track,
                    "provider":       self._provider_name,
                    "total_tokens":   total_tokens,
                    "duration_ms":    _now_ms() - start_ms,
                    "expert_count":   len(all_expert_results),
                    "gate_verdicts":  gate_verdicts,
                    "warning_count":  len(warnings),
                },
                session_id=session_id,
            )
            # Append gate verdicts to rolling history atom
            if gate_verdicts:
                verdicts_section = (
                    f"## Session {session_id[:8]} — {_iso_now()}\n\n"
                    + "\n".join(f"- **{g}**: {v}" for g, v in gate_verdicts.items())
                    + "\n"
                )
                self._engram.append("gates/verdicts.md", verdicts_section, session_id)

            self._log(session_id, "PHASE_8", "session_close", "COMPLETED", 1, 0,
                      {"total_tokens": total_tokens, "engram_written": True})

            _result_for_index = AsyncSessionResult(
                session_id=session_id,
                objective=objective,
                status="completed",
                expert_results=all_expert_results,
                gate_verdicts=gate_verdicts,
                total_tokens=total_tokens,
                duration_ms=_now_ms() - start_ms,
                warnings=warnings,
            )
            return _result_for_index

        finally:
            if self._broker:
                self._broker.close()
            if self._telemetry:
                if _result_for_index is not None:
                    self._telemetry.write_index_entry(
                        _build_index_entry(_result_for_index, classification, self._provider_name)
                    )
                self._telemetry.close()

    # ------------------------------------------------------------------
    # BiasAuditAgent — PHASE 1.5 (L2 tasks only)
    # ------------------------------------------------------------------

    async def _run_bias_audit(
        self,
        session_id: str,
        dag: DAG,
        objective: str,
        classification: ClassificationResult,
    ) -> tuple[bool, str, list[str]]:
        """Invoke BiasAuditAgent and validate output deterministically.

        Runs as PHASE 1.5 — after DAG confirmed, before PHASE 5 expert execution.
        Only activates for complexity level == 2 (architectural tasks).

        Flow:
            1. Load bias_auditor agent config (loader, Tier 1)
            2. Load bias-audit skill (SHA-256 verified, Tier 1)
            3. Build system prompt: agent + contract + base + skill
            4. Call LLM provider (Tier 3 — same provider as L2 experts)
            5. validate_bias_output() — Tier 1 deterministic check
            6. Emit GATE_VERDICT(APPROVED) or log missing sections
            7. Emit CHECKPOINT_REQ after audit completes

        Returns:
            tuple(approved: bool, output_text: str, missing_sections: list[str])
        """
        self._log(session_id, "PHASE_1_5", "bias_audit_start", "OK", 1, 0, {
            "dag_nodes": len(dag.nodes),
            "complexity": classification.level,
        })

        # Tier 1 — load agent config (no LLM)
        try:
            agent_cfg  = self._loader.load_agent("bias_auditor")
            skill_cfg  = self._loader.load_skill("bias-audit")
        except (FileNotFoundError, PermissionError) as exc:
            self._log(session_id, "PHASE_1_5", "bias_audit_load_error", "WARN", 1, 0,
                      {"error": str(exc)})
            # Non-fatal: if agent files missing, skip audit with warning
            return True, "", []

        # Build system prompt: agent identity + contract + base contract + skill
        system_prompt = (
            f"{agent_cfg.agent_md}\n\n"
            f"--- CONTRACT ---\n{agent_cfg.contract_md}\n\n"
            f"--- BASE CONTRACT ---\n{agent_cfg.base_md}\n\n"
            f"--- BIAS AUDIT SKILL ---\n{skill_cfg.content}"
        )

        # Build user message: DAG proposal + objective for audit
        node_descriptions = "\n".join(
            f"- [{n.node_id}] domain={n.domain}: {n.description} "
            f"(files: {', '.join(n.files_in_scope) or 'TBD'})"
            for n in dag.nodes
        )
        user_message = (
            f"## Architectural Proposal to Audit\n\n"
            f"**Objective:** {objective}\n\n"
            f"**Complexity:** Level {classification.level}\n\n"
            f"**DAG nodes ({len(dag.nodes)}):**\n{node_descriptions}\n\n"
            f"Apply all four Audit Directives (Ecosystem Neutrality, "
            f"Red Teaming Semántico, Multi-LLM Interoperability Audit, "
            f"Deterministic Logic Preservation).\n\n"
            f"Your output MUST end with the complete "
            f"'## Análisis de Sesgos y Dependencias' section."
        )

        # Tier 3 — LLM call (BiasAuditAgent is L1 → always cloud)
        provider = self._router.get_provider(
            self._router.resolve_tier("L1")
        )
        # Model registry: bias_auditor → FLAGSHIP (architectural decisions, high risk)
        bias_model = resolve_model("bias_auditor", self._provider_name)

        output_text = ""
        if provider is not None:
            try:
                req = ProviderRequest(
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    model=bias_model,
                    max_tokens=4096,
                )
                resp: ProviderResponse = await provider.complete(req)
                output_text = resp.content
                self._log(session_id, "PHASE_1_5", "bias_audit_llm", "OK",
                          resp.input_tokens + resp.output_tokens, resp.output_tokens, {
                              "provider": type(provider).__name__,
                              "model":    resp.model,
                          })
            except Exception as exc:  # noqa: BLE001
                self._log(session_id, "PHASE_1_5", "bias_audit_llm_error", "WARN", 1, 0,
                          {"error": str(exc)[:200]})
                # LLM failure → skip audit (non-fatal) to avoid blocking session
                return True, "", []
        else:
            # No provider available (e.g. Tier 3 not configured) → skip
            self._log(session_id, "PHASE_1_5", "bias_audit_no_provider", "WARN", 1, 0, {})
            return True, "", []

        # Tier 1 — deterministic validation
        validation: BiasValidationResult = validate_bias_output(output_text)

        # Log warnings regardless of pass/fail
        for w in validation.warnings:
            self._log(session_id, "PHASE_1_5", "bias_audit_warning", "WARN", 1, 0,
                      {"warning": w})
        for risk in validation.lock_in_risks:
            self._log(session_id, "PHASE_1_5", "bias_audit_lock_in", "WARN", 1, 0,
                      {"risk": risk})

        if validation.valid:
            # PMIA: APPROVED gate verdict
            self._broker.send(gate_verdict(
                agent_id="BiasAuditAgent",
                session_id=session_id,
                gate=GateId.GATE_1,
                verdict=Verdict.APPROVED,
                rationale=(
                    f"BiasAudit passed. red_team={validation.red_team_result} "
                    f"multi_llm={validation.multi_llm_result}"
                ),
            ))
            self._log(session_id, "PHASE_1_5", "bias_audit_verdict", "APPROVED", 1, 0, {
                "red_team": validation.red_team_result,
                "multi_llm": validation.multi_llm_result,
            })
        else:
            self._log(session_id, "PHASE_1_5", "bias_audit_verdict", "REJECTED", 1, 0, {
                "missing": validation.missing_sections,
            })

        # PMIA: checkpoint after audit regardless of outcome
        self._broker.send(checkpoint_req(
            agent_id="BiasAuditAgent",
            session_id=session_id,
            phase="PHASE_1_5",
            state_summary=(
                f"BiasAudit {'PASSED' if validation.valid else 'REJECTED'}. "
                f"red_team={validation.red_team_result} "
                f"multi_llm={validation.multi_llm_result} "
                f"missing={len(validation.missing_sections)}."
            ),
        ))

        return validation.valid, output_text, validation.missing_sections

    # ------------------------------------------------------------------
    # Parallel specialist execution
    # ------------------------------------------------------------------

    async def _run_specialist(
        self,
        session_id: str,
        node: DAGNode,
        classification: ClassificationResult,
    ) -> ExpertResult:
        """Run a single SpecialistAgent as an async LLM call.

        Each expert is fully independent — system prompt comes from the
        agent's markdown files; task context from its spec section.
        Provider/model is chosen by ProviderRouter based on complexity level:
          Level 1 → agent_level L2 → Tier 2 (Ollama) if available, else Tier 3
          Level 2 → agent_level L1 → Tier 3 always (cloud, genuine reasoning required)
        """
        start_ms = _now_ms()
        expert_id = f"SpecialistAgent-{session_id[:8]}-{node.node_id}"
        wt_name   = f"{session_id[:8]}-{node.node_id}"

        # Route provider via ProviderRouter — complexity drives agent_level
        agent_level = _COMPLEXITY_TO_AGENT_LEVEL.get(classification.level, "L1")
        tier        = self._router.resolve_tier(agent_level)
        provider    = self._router.get_provider(tier)

        # Model registry: specialist_agent gets FAST for complexity=1, BALANCED for complexity=2
        model = resolve_model(
            "specialist_agent",
            self._provider_name,
            task_complexity=classification.level,
        )

        self._log(session_id, "PHASE_5", "provider_routed", "OK", tier.value, 0, {
            "node_id":      node.node_id,
            "complexity":   classification.level,
            "agent_level":  agent_level,
            "tier":         tier.name,
            "provider":     type(provider).__name__ if provider else "none",
            "model":        model,
        })

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

            request = ProviderRequest(
                messages=messages,
                model=model,
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

    def _handle_escalation(self, msg: PMIAMessage) -> None:
        """Item 38 — enforce fragmentation depth ≤ 2 for CONTEXT_SATURATION escalations.

        Registered on PMIABroker for MessageType.ESCALATION.
        When SecurityAgent (or any agent) escalates CONTEXT_SATURATION, depth is
        incremented. If depth exceeds _MAX_FRAGMENTATION_DEPTH, a PROTOCOL_VIOLATION
        escalation is sent instead of allowing further fragmentation.
        """
        if msg.payload.get("reason") != EscalationReason.CONTEXT_SATURATION.value:
            return

        self._fragmentation_depth += 1

        if self._fragmentation_depth > _MAX_FRAGMENTATION_DEPTH:
            import logging as _logging
            _logging.getLogger(__name__).error(
                "[AsyncSession] CONTEXT_SATURATION depth %d exceeds max %d for agent %s — "
                "fragmentation blocked, emitting PROTOCOL_VIOLATION",
                self._fragmentation_depth,
                _MAX_FRAGMENTATION_DEPTH,
                msg.agent_id,
            )
            if self._broker:
                self._broker.send(escalation(
                    agent_id="AsyncSession",
                    session_id=msg.session_id,
                    reason=EscalationReason.PROTOCOL_VIOLATION,
                    context=(
                        f"Fragmentation depth {self._fragmentation_depth} exceeds "
                        f"max {_MAX_FRAGMENTATION_DEPTH} — agent {msg.agent_id} blocked."
                    ),
                ))

    def _bootstrap_providers(self) -> None:
        """Initialise async provider instances and wire ProviderRouter."""
        from sdk.providers.anthropic_async import AsyncAnthropicProvider
        from sdk.providers.ollama_async import AsyncOllamaProvider

        if self._provider_name in ("anthropic", "openai"):
            self._cloud = AsyncAnthropicProvider(model=self._model or "claude-sonnet-4-6")
        elif self._provider_name == "ollama":
            self._local = AsyncOllamaProvider(model=self._model or "llama3.2:3b")

        if self._local_model:
            self._local = AsyncOllamaProvider(model=self._local_model)

        # ProviderRouter owns all tier/level routing decisions going forward.
        # It checks is_available() internally for Tier 2 fallback.
        self._router = ProviderRouter(
            cloud_provider=self._cloud,
            local_provider=self._local,
        )

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


def _iso_now() -> str:
    import time as _t
    return _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime())


def _build_index_entry(
    result: AsyncSessionResult,
    classification: ClassificationResult,
    provider: str,
) -> dict:
    """Build the compact summary written to logs/index.jsonl.

    One line per session — queryable with jq:
        jq 'select(.status=="failed")' logs/index.jsonl
        jq 'select(.complexity_level==2)' logs/index.jsonl
        jq '[.total_tokens] | add' logs/index.jsonl
    """
    return {
        "session_id":      result.session_id,
        "objective":       result.objective[:120],
        "status":          result.status,
        "complexity_level": classification.level,
        "fast_track":      classification.fast_track,
        "provider":        provider,
        "total_tokens":    result.total_tokens,
        "duration_ms":     result.duration_ms,
        "expert_count":    len(result.expert_results),
        "gate_verdicts":   result.gate_verdicts,
        "warning_count":   len(result.warnings),
    }
