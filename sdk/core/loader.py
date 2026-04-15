"""sdk/core/loader.py — FrameworkLoader: reads agents/, contracts/, skills/ at runtime.

Load authorization per sys/_index.md §Load Table by Role.
Every load_agent_for_role() call is checked against the role's authorized list.
Violations are logged — ExecutionAuditor monitors for them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from sdk.utils.sha256 import SHA256Verifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role-based load authorization table
# Mirrors sys/_index.md §Load Table by Role exactly.
# Keys: requesting role. Values: set of agent names that role may load.
# ---------------------------------------------------------------------------

_AUTHORIZED_LOADS: dict[str, set[str]] = {
    "orchestrator": {
        "orchestrator",
    },
    "security_agent": {
        "security_agent",
    },
    "audit_agent": {
        "audit_agent",
    },
    "coherence_agent": {
        "coherence_agent",
    },
    "compliance_agent": {
        "compliance_agent",
    },
    "evaluation_agent": {
        "evaluation_agent",
    },
    "standards_agent": {
        "standards_agent",
    },
    "documentation_agent": {
        "documentation_agent",
    },
    "research_orchestrator": {
        "research_orchestrator",
    },
    "logistics_agent": {
        "logistics_agent",
    },
    "execution_auditor": {
        "execution_auditor",
    },
    "domain_orchestrator": {
        "domain_orchestrator",
    },
    "specialist_agent": {
        "specialist_agent",
    },
    "bias_auditor": {
        "bias_auditor",
    },
    # Internal bootstrap — session layer may load any agent to instantiate them
    "_session": {
        "orchestrator", "security_agent", "audit_agent", "coherence_agent",
        "compliance_agent", "evaluation_agent", "standards_agent",
        "documentation_agent", "research_orchestrator", "logistics_agent",
        "execution_auditor", "domain_orchestrator", "specialist_agent",
        "bias_auditor",
    },
}


@dataclass
class AgentConfig:
    """Parsed representation of an agent's three markdown files."""

    name: str
    agent_md: str      # content of agents/<name>.md
    contract_md: str   # content of contracts/<name>.md
    base_md: str       # content of contracts/_base.md


@dataclass
class SkillConfig:
    """Parsed representation of a verified skill module."""

    name: str
    content: str


class FrameworkLoader:
    """Load framework markdown files from the repository root at runtime.

    Supports two deployment modes:
      Mode 1 (clone): root = repo root
      Mode 2 (pip install): root = package root (markdowns bundled via package_data)

    Invariant: no file is loaded unless explicitly requested by the caller.
    All skill loads are SHA-256 verified against skills/manifest.json.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    # ------------------------------------------------------------------
    # Agent loading
    # ------------------------------------------------------------------

    def load_agent(self, name: str) -> AgentConfig:
        """Load an agent's config from its three defining markdown files.

        Args:
            name: Agent identifier (e.g. "orchestrator", "security_agent").

        Returns:
            AgentConfig with all three file contents populated.

        Raises:
            FileNotFoundError: If any required markdown file is missing.
        """
        agent_path    = self.root / "agents"    / f"{name}.md"
        contract_path = self.root / "contracts" / f"{name}.md"
        base_path     = self.root / "contracts" / "_base.md"

        for p in (agent_path, base_path):
            if not p.exists():
                raise FileNotFoundError(f"Required framework file not found: {p}")

        # contracts/<name>.md may not exist for all agents (e.g. research_orchestrator
        # uses _base.md directly) — load if present, otherwise empty string.
        contract_content = (
            contract_path.read_text(encoding="utf-8")
            if contract_path.exists()
            else ""
        )

        return AgentConfig(
            name=name,
            agent_md=agent_path.read_text(encoding="utf-8"),
            contract_md=contract_content,
            base_md=base_path.read_text(encoding="utf-8"),
        )

    # ------------------------------------------------------------------
    # Skill loading (SHA-256 verified)
    # ------------------------------------------------------------------

    def load_skill(self, name: str) -> SkillConfig:
        """Load and verify a skill module.

        Args:
            name: Skill name without extension (e.g. "observability").

        Returns:
            SkillConfig with the verified content.

        Raises:
            FileNotFoundError: If the skill file or manifest is missing.
            SHA256VerificationError: If the hash does not match the manifest.
        """
        manifest = self.root / "skills" / "manifest.json"
        SHA256Verifier.verify(name, manifest)

        skill_path = self.root / "skills" / f"{name}.md"
        return SkillConfig(
            name=name,
            content=skill_path.read_text(encoding="utf-8"),
        )

    # ------------------------------------------------------------------
    # Role-authorized agent loading (sys/_index.md load table enforcement)
    # ------------------------------------------------------------------

    def load_agent_for_role(self, name: str, requesting_role: str) -> AgentConfig:
        """Load an agent config, enforcing the role-based authorization table.

        Args:
            name:            Agent to load (e.g. "specialist_agent").
            requesting_role: Role of the agent making the request.
                             Use "_session" for internal session-layer loads.

        Returns:
            AgentConfig — same as load_agent().

        Raises:
            PermissionError: If requesting_role is not authorized to load name.
            FileNotFoundError: If the agent files are missing.
        """
        authorized = _AUTHORIZED_LOADS.get(requesting_role, set())
        if name not in authorized:
            violation_msg = (
                f"[LoadViolation] role '{requesting_role}' attempted to load "
                f"agent '{name}' — not in authorized list. "
                f"Authorized: {sorted(authorized) or 'none'}. "
                f"See sys/_index.md §Load Table by Role."
            )
            logger.error(violation_msg)
            raise PermissionError(violation_msg)

        logger.debug("[FrameworkLoader] authorized: %s → %s", requesting_role, name)
        return self.load_agent(name)

    # ------------------------------------------------------------------
    # sys/ loading
    # ------------------------------------------------------------------

    def load_sys(self, filename: str) -> str:
        """Load a sys/ file by name (e.g. '_index.md', '_verify.md').

        Returns:
            File content as a string.
        """
        path = self.root / "sys" / filename
        if not path.exists():
            raise FileNotFoundError(f"sys/ file not found: {path}")
        return path.read_text(encoding="utf-8")
