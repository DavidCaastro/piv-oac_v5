"""sdk/core/model_registry.py — Agent-to-model resolution (Tier 1, deterministic).

Maps every PIV/OAC agent to the correct model per provider, following the
principle from contracts/models.md (v4) and skills/provider-routing.md:

    FLAGSHIP  — highest capability, highest cost
                Used for: orchestration, security, bias audit.
                Rationale: high ambiguity, high risk, graph construction,
                multi-trade-off decisions.

    BALANCED  — mid-tier reasoning, moderate cost
                Used for: domain orchestrators, standards, compliance,
                evaluation, complex specialist tasks.
                Rationale: structured planning, pattern generation,
                coordination with clear goals.

    FAST      — low cost, high throughput, structured output
                Used for: audit (routine), coherence (standard gate),
                logistics, execution auditor, documentation (structured),
                simple specialist tasks.
                Rationale: mechanical transformation, lookup, formatting,
                clear validation rules.

Dynamic escalation (mirrors v4 contracts/models.md v3.0):
    audit_agent + coherence_agent:  FAST by default → BALANCED on MAYOR/CRITICAL
    documentation_agent:            FAST by default → BALANCED on design inference
    specialist_agent:               complexity=1 → FAST, complexity=2 → BALANCED

Provider × tier → model (kept current as of 2026-04-16):
    anthropic: opus-4-6 / sonnet-4-6 / haiku-4-5-20251001
    openai:    gpt-4o   / gpt-4o      / gpt-4o-mini
    ollama:    qwen2.5-coder:32b / :14b / :7b
    gemini:    gemini-2.0-flash-exp / gemini-2.0-flash / gemini-2.0-flash
"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# ModelTier
# ---------------------------------------------------------------------------

class ModelTier(str, Enum):
    """Capability tier — provider-agnostic."""

    FLAGSHIP = "flagship"   # highest capability
    BALANCED = "balanced"   # mid-tier reasoning
    FAST     = "fast"       # low-cost, high-throughput


# ---------------------------------------------------------------------------
# Agent → base tier (before dynamic escalation)
# ---------------------------------------------------------------------------

_AGENT_BASE_TIERS: dict[str, ModelTier] = {
    # ── L0 — Master Orchestrator ──────────────────────────────────────────
    "orchestrator":          ModelTier.FLAGSHIP,

    # ── L1 — Critical gatekeepers (FLAGSHIP: high risk, veto authority) ──
    "security_agent":        ModelTier.FLAGSHIP,
    "bias_auditor":          ModelTier.FLAGSHIP,

    # ── L1 — Control agents (FAST default, escalated to BALANCED) ─────────
    "audit_agent":           ModelTier.FAST,
    "coherence_agent":       ModelTier.FAST,

    # ── L1 — Standards/compliance (BALANCED: needs reasoning, clear goal) ─
    "standards_agent":       ModelTier.BALANCED,
    "compliance_agent":      ModelTier.BALANCED,
    "evaluation_agent":      ModelTier.BALANCED,

    # ── L1 — Documentation (FAST structured, BALANCED on design inference) ─
    "documentation_agent":   ModelTier.FAST,

    # ── L1 — Logistics / execution monitoring (FAST: routine, deterministic)
    "logistics_agent":       ModelTier.FAST,
    "execution_auditor":     ModelTier.FAST,

    # ── L1.5 — Domain orchestrators (BALANCED: coordinate, plan, delegate) ─
    "domain_orchestrator":   ModelTier.BALANCED,
    "research_orchestrator": ModelTier.BALANCED,

    # ── L2 — Specialist agents (BALANCED complex / FAST atomic) ───────────
    # Actual tier resolved dynamically by task_complexity.
    "specialist_agent":      ModelTier.BALANCED,
}


# ---------------------------------------------------------------------------
# Provider × tier → model string
# ---------------------------------------------------------------------------

_PROVIDER_MODELS: dict[str, dict[ModelTier, str]] = {
    "anthropic": {
        ModelTier.FLAGSHIP: "claude-opus-4-6",
        ModelTier.BALANCED: "claude-sonnet-4-6",
        ModelTier.FAST:     "claude-haiku-4-5-20251001",
    },
    "openai": {
        ModelTier.FLAGSHIP: "gpt-4o",
        ModelTier.BALANCED: "gpt-4o",
        ModelTier.FAST:     "gpt-4o-mini",
    },
    "ollama": {
        ModelTier.FLAGSHIP: "qwen2.5-coder:32b",
        ModelTier.BALANCED: "qwen2.5-coder:14b",
        ModelTier.FAST:     "qwen2.5-coder:7b",
    },
    "gemini": {
        ModelTier.FLAGSHIP: "gemini-2.0-flash-exp",
        ModelTier.BALANCED: "gemini-2.0-flash",
        ModelTier.FAST:     "gemini-2.0-flash",
    },
}

# Fallback when provider not in registry
_FALLBACK_PROVIDER = "anthropic"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_model(
    agent_name: str,
    provider_name: str,
    *,
    task_complexity: int = 1,
    escalate: bool = False,
) -> str:
    """Return the model string for a given agent + provider combination.

    Args:
        agent_name:      Agent identifier matching _AGENT_BASE_TIERS keys.
                         Unknown agents default to BALANCED.
        provider_name:   Provider key: "anthropic" | "openai" | "ollama" | "gemini".
                         Unknown providers fall back to "anthropic" mapping.
        task_complexity: Complexity classifier level (1 or 2).
                         Affects specialist_agent tier selection.
        escalate:        True when the calling context is a MAYOR/CRITICAL
                         conflict or design-inference task.
                         Promotes FAST agents to BALANCED for that invocation.

    Returns:
        Model string ready to set on ProviderRequest.model.

    Examples:
        >>> resolve_model("orchestrator", "anthropic")
        'claude-opus-4-6'
        >>> resolve_model("specialist_agent", "anthropic", task_complexity=1)
        'claude-haiku-4-5-20251001'
        >>> resolve_model("audit_agent", "openai", escalate=True)
        'gpt-4o'
    """
    tier = _resolve_tier(agent_name, task_complexity=task_complexity, escalate=escalate)
    provider_map = _PROVIDER_MODELS.get(provider_name) or _PROVIDER_MODELS[_FALLBACK_PROVIDER]
    return provider_map[tier]


def agent_tier(agent_name: str) -> ModelTier:
    """Return the base ModelTier for an agent (before escalation).

    Useful for logging and telemetry without a provider context.
    """
    return _AGENT_BASE_TIERS.get(agent_name, ModelTier.BALANCED)


def supported_providers() -> list[str]:
    """Return list of providers with a model mapping."""
    return list(_PROVIDER_MODELS.keys())


# ---------------------------------------------------------------------------
# Internal escalation logic
# ---------------------------------------------------------------------------

def _resolve_tier(
    agent_name: str,
    *,
    task_complexity: int,
    escalate: bool,
) -> ModelTier:
    """Apply dynamic escalation rules on top of the base tier."""
    base = _AGENT_BASE_TIERS.get(agent_name, ModelTier.BALANCED)

    # specialist_agent: complexity-driven (overrides escalate flag)
    if agent_name == "specialist_agent":
        return ModelTier.FAST if task_complexity < 2 else ModelTier.BALANCED

    # audit_agent, coherence_agent, documentation_agent:
    # FAST by default, promoted to BALANCED on escalation signal
    if escalate and base == ModelTier.FAST:
        return ModelTier.BALANCED

    return base
