"""sdk/core/loader.py — FrameworkLoader: reads agents/, contracts/, skills/ at runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdk.utils.sha256 import SHA256Verifier


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
