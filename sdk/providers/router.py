"""sdk/providers/router.py — Tier routing per operation (Tier 1, deterministic)."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider


class Tier(IntEnum):
    """Execution tier.

    TIER1 — local deterministic (no LLM)
    TIER2 — local inference via Ollama (optional)
    TIER3 — cloud inference (Anthropic / OpenAI)
    """

    TIER1 = 1
    TIER2 = 2
    TIER3 = 3


class ProviderRouter:
    """Select the correct provider based on operation tier and agent level.

    Rule (from _context_.md §9 Tier Routing Rule):
      Deterministically resolvable?  → Tier 1 (no provider returned)
      Mechanical + local_model set?  → Tier 2 (Ollama)
      Requires genuine reasoning?    → Tier 3 (cloud)
    """

    # Agent level → default tier (without local_model)
    _LEVEL_DEFAULT: dict[str, Tier] = {
        "L0": Tier.TIER3,
        "L1": Tier.TIER3,
        "L1.5": Tier.TIER3,
        "L2": Tier.TIER3,
    }

    # Agent level → tier when local_model is configured
    _LEVEL_WITH_LOCAL: dict[str, Tier] = {
        "L0": Tier.TIER3,    # cloud required — complexity too high for local
        "L1": Tier.TIER3,    # cloud required — reasoning + veto authority
        "L1.5": Tier.TIER2,  # structured plan → local adequate
        "L2": Tier.TIER2,    # mechanical code → local adequate
    }

    def __init__(
        self,
        cloud_provider: "BaseProvider | None" = None,
        local_provider: "BaseProvider | None" = None,
    ) -> None:
        self._cloud = cloud_provider
        self._local = local_provider

    def resolve_tier(self, agent_level: str, is_deterministic: bool = False) -> Tier:
        """Determine which tier an operation should run on.

        Args:
            agent_level: "L0", "L1", "L1.5", or "L2".
            is_deterministic: True if the operation is purely computational.

        Returns:
            The resolved Tier.
        """
        if is_deterministic:
            return Tier.TIER1

        if self._local is not None and self._local.is_available():
            return self._LEVEL_WITH_LOCAL.get(agent_level, Tier.TIER3)

        return self._LEVEL_DEFAULT.get(agent_level, Tier.TIER3)

    def get_provider(self, tier: Tier) -> "BaseProvider | None":
        """Return the provider instance for *tier*, or None for Tier 1."""
        if tier == Tier.TIER1:
            return None
        if tier == Tier.TIER2:
            # Fallback to cloud if local is unavailable
            if self._local and self._local.is_available():
                return self._local
            return self._cloud
        return self._cloud  # Tier 3
