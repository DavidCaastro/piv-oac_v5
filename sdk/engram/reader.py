"""sdk/engram/reader.py — EngramReader: role-scoped, read-only engram access."""

from __future__ import annotations

from pathlib import Path


class EngramAccessError(Exception):
    """Raised when an agent requests an engram atom outside its allowed scope."""


# Role → allowed subdirectories (relative to engram/)
_ROLE_SCOPE: dict[str, frozenset[str]] = {
    "orchestrator":        frozenset({"core", "domains"}),
    "security_agent":      frozenset({"security"}),
    "audit_agent":         frozenset({"core", "domains", "security", "audit", "metrics"}),
    "coherence_agent":     frozenset({"core"}),
    "compliance_agent":    frozenset({"core", "audit"}),
    "evaluation_agent":    frozenset({"metrics"}),
    "standards_agent":     frozenset({"core"}),
    "documentation_agent": frozenset({"core", "domains"}),
    "research_orchestrator": frozenset({"core"}),
    "domain_orchestrator": frozenset({"core", "domains"}),
    # specialist_agent: no engram access (isolation boundary)
}

# AuditAgent has write access — all other agents are read-only.
_WRITE_AUTHORIZED: frozenset[str] = frozenset({"audit_agent"})


class EngramReader:
    """Mediated, read-only access to engram atoms.

    Agents declare which atom they need and why.
    This class enforces:
      - Role-based scope (agent X can only read from allowed subdirs)
      - Read-only for all agents except AuditAgent
      - Lazy loading: atoms are never pre-loaded; each call is explicit

    Usage:
        reader = EngramReader(engram_root=Path("engram"), role="orchestrator")
        text = reader.read("core/decisions.md")
    """

    def __init__(self, engram_root: Path, role: str) -> None:
        self._root = engram_root
        self._role = role
        self._allowed = _ROLE_SCOPE.get(role, frozenset())

    def read(self, atom_path: str) -> str:
        """Read an engram atom at *atom_path* (relative to engram/).

        Args:
            atom_path: E.g. "core/decisions.md" or "security/alerts.md".

        Returns:
            File content as a string.

        Raises:
            EngramAccessError: If the role is not allowed to read this atom.
            FileNotFoundError: If the atom does not exist.
        """
        self._check_scope(atom_path)

        full_path = self._root / atom_path
        if not full_path.exists():
            raise FileNotFoundError(f"Engram atom not found: {full_path}")

        return full_path.read_text(encoding="utf-8")

    def exists(self, atom_path: str) -> bool:
        """Return True if the atom exists and the role has scope to read it."""
        try:
            self._check_scope(atom_path)
        except EngramAccessError:
            return False
        return (self._root / atom_path).exists()

    def _check_scope(self, atom_path: str) -> None:
        subdir = atom_path.split("/")[0]

        if "specialist_agent" in self._role:
            raise EngramAccessError(
                f"SpecialistAgent has no engram access (isolation boundary). "
                f"Requested: {atom_path}"
            )

        if subdir not in self._allowed:
            raise EngramAccessError(
                f"Role '{self._role}' is not allowed to read engram/{subdir}/. "
                f"Allowed: {sorted(self._allowed)}"
            )
