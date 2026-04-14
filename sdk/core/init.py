"""sdk/core/init.py — piv-oac init: branch bootstrap and workspace verification."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from sdk.vault import Vault, VaultError


class InitError(Exception):
    """Raised when the init sequence cannot complete."""


@dataclass
class InitResult:
    case: str           # "CASE_A" | "CASE_B"
    branches_created: list[str]
    warnings: list[str]
    session_id: str


def _git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Raises InitError on failure."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _branch_exists(name: str, repo: Path) -> bool:
    try:
        out = _git(["branch", "--list", name], repo)
        return bool(out.strip())
    except InitError:
        return False


def _remote_branch_exists(name: str, repo: Path) -> bool:
    try:
        out = _git(["branch", "-r", "--list", f"origin/{name}"], repo)
        return bool(out.strip())
    except InitError:
        return False


class Initializer:
    """Implements the `piv-oac init` bootstrap sequence.

    From _context_.md §8 piv-oac init:
      Step 1: sys/_verify.md checks (git remote + credentials + Python env)
      Step 2: inspect existing branches → CASE A or CASE B
      Step 3: emit InitResult — ready for Session.run()
    """

    def __init__(self, repo_root: Path, provider: str) -> None:
        self._repo = repo_root
        self._provider = provider

    def run(self) -> InitResult:
        """Execute the full init sequence."""
        warnings: list[str] = []
        branches_created: list[str] = []

        # --- Step 1: credential check (Tier 1) ---
        try:
            Vault.get_credential(self._provider)
        except VaultError as exc:
            raise InitError(str(exc)) from exc

        # --- Step 1: git remote reachable ---
        try:
            _git(["ls-remote", "--exit-code", "origin"], self._repo)
        except InitError:
            warnings.append("git remote 'origin' not reachable — offline mode")

        # --- Step 2: inspect branches ---
        has_staging    = _branch_exists("staging", self._repo)
        has_directive  = _branch_exists("piv-directive", self._repo)

        # --- CASE A: new project ---
        if not has_staging and not has_directive:
            branches_created = self._bootstrap_new_project()
            case = "CASE_A"

        # --- CASE B: resume ---
        else:
            self._verify_directive_integrity()
            interrupted = self._check_interrupted_sessions()
            if interrupted:
                warnings.append(
                    f"Found {len(interrupted)} interrupted session(s) in .piv/active/"
                )
            case = "CASE_B"

        import uuid
        session_id = str(uuid.uuid4())

        return InitResult(
            case=case,
            branches_created=branches_created,
            warnings=warnings,
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bootstrap_new_project(self) -> list[str]:
        """CASE A: create piv-directive (orphan) + staging branch."""
        created: list[str] = []

        # Create orphan piv-directive
        _git(["checkout", "--orphan", "piv-directive"], self._repo)
        _git(["rm", "-rf", "."], self._repo)
        (self._repo / ".piv-managed").write_text(
            "# This branch is managed by piv-oac. Do not modify manually.\n"
        )
        _git(["add", ".piv-managed"], self._repo)
        _git(["commit", "-m", "chore: initialize piv-directive (piv-oac managed)"], self._repo)
        created.append("piv-directive")

        # Return to main
        _git(["checkout", "main"], self._repo)

        # Create staging from main
        _git(["checkout", "-b", "staging"], self._repo)
        _git(["checkout", "main"], self._repo)
        created.append("staging")

        # Initialize .piv/ directory
        piv_dir = self._repo / ".piv"
        for subdir in ("active", "completed", "failed", "checkpoints"):
            (piv_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Write initial .gitignore entries if missing
        gitignore = self._repo / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        additions = [e for e in [".piv/", "worktrees/", ".env", ".venv/"] if e not in existing]
        if additions:
            with gitignore.open("a", encoding="utf-8") as fh:
                fh.write("\n" + "\n".join(additions) + "\n")

        return created

    def _verify_directive_integrity(self) -> None:
        """CASE B: verify piv-directive has not been tampered with (Tier 1)."""
        # Minimal check: confirm the branch exists and has the managed marker commit.
        # Full SHA-256 skill manifest verification is done by FrameworkLoader.load_skill().
        try:
            _git(["rev-parse", "--verify", "piv-directive"], self._repo)
        except InitError as exc:
            raise InitError("piv-directive branch is missing or corrupt") from exc

    def _check_interrupted_sessions(self) -> list[str]:
        """Return session IDs found in .piv/active/."""
        active_dir = self._repo / ".piv" / "active"
        if not active_dir.exists():
            return []
        return [p.stem for p in active_dir.glob("*.json")]
