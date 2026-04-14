"""sdk/tools/executor.py — SafeLocalExecutor.

Lets agents delegate tasks to local scripts via a strict allowlist.
All arguments are filtered through ExecutionDataFilter before execution.

Allowlisted commands (ALLOWED_COMMANDS):
    "worktree_add"    → bash sys/bootstrap.sh wt:add     (create worktree)
    "worktree_remove" → bash sys/bootstrap.sh wt:remove  (remove worktree)
    "worktree_list"   → bash sys/bootstrap.sh wt:list    (list worktrees)
    "worktree_prune"  → bash sys/bootstrap.sh wt:prune   (remove stale refs)
    "run_pytest"      → python -m pytest                  (Gate 2b mandatory)
    "run_lint"        → bash sys/bootstrap.sh lint        (ruff check + format)
    "validate"        → bash sys/bootstrap.sh validate    (sys/_verify.md checks)

Usage:
    executor = SafeLocalExecutor(project_root=Path("."))

    # Worktree lifecycle (DomainOrchestrator — PHASE 5)
    result = await executor.run("worktree_add", ["auth-001", "expert-1"])

    # Gate 2b — pytest MUST pass before EvaluationAgent/StandardsAgent LLM call
    result = await executor.run("run_pytest", ["--cov=sdk", "-q"])
    if not result.success:
        # BLOCKED_BY_TOOL — do NOT invoke LLM agents
        raise BlockedByToolError(result.to_agent_summary())
    standards_prompt = f"pytest output:\n{result.to_agent_summary()}"
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .filter import ExecutionDataFilter, FilterError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

_ALLOWED_COMMANDS: dict[str, list[str]] = {
    "worktree_add":    ["bash", "sys/bootstrap.sh", "wt:add"],
    "worktree_remove": ["bash", "sys/bootstrap.sh", "wt:remove"],
    "worktree_list":   ["bash", "sys/bootstrap.sh", "wt:list"],
    "worktree_prune":  ["bash", "sys/bootstrap.sh", "wt:prune"],
    "run_pytest":      ["python", "-m", "pytest"],
    "run_lint":        ["bash", "sys/bootstrap.sh", "lint"],
    "validate":        ["bash", "sys/bootstrap.sh", "validate"],
}

_DEFAULT_TIMEOUT   = 60.0     # seconds
_MAX_OUTPUT_BYTES  = 32_768   # 32 KB — prevents context pollution in agent prompts


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionResult:
    """Structured result of a local script execution."""

    command: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    truncated: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def to_agent_summary(self) -> str:
        """Compact summary safe to embed in an agent prompt.

        Truncated to _MAX_OUTPUT_BYTES — never bloats the LLM context window.
        """
        status = "SUCCESS" if self.success else f"FAILED (exit {self.returncode})"
        trunc  = " [OUTPUT TRUNCATED]" if self.truncated else ""
        return (
            f"LOCAL_EXEC: {self.command} {' '.join(self.args)}\n"
            f"STATUS: {status}{trunc}\n"
            f"STDOUT:\n{self.stdout}\n"
            f"STDERR:\n{self.stderr}"
        ).strip()


class BlockedByToolError(Exception):
    """Raised when a Gate 2b tool check fails — LLM agents must not be invoked."""


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class SafeLocalExecutor:
    """Executes pre-approved local scripts on behalf of agents.

    Security guarantees:
    - Only commands in ALLOWED_COMMANDS may be invoked.
    - All arguments are validated by ExecutionDataFilter before execution.
    - No shell=True — arguments are passed as a list (no shell injection).
    - Hard wall-clock timeout per execution.
    - Output truncated to MAX_OUTPUT_BYTES before returning to agents.

    Parameters:
        project_root: Repository root. Used to locate sys/bootstrap.sh
                      and as base for path validation in ExecutionDataFilter.
        timeout:      Wall-clock timeout per execution in seconds.
    """

    ALLOWED_COMMANDS = _ALLOWED_COMMANDS

    def __init__(
        self,
        project_root: Path | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._root    = (project_root or Path.cwd()).resolve()
        self._timeout = timeout
        self._filter  = ExecutionDataFilter(base_dir=self._root)

    async def run(self, command: str, args: list[str] | None = None) -> ExecutionResult:
        """Execute an allowlisted command with validated arguments.

        Args:
            command: Key in ALLOWED_COMMANDS (e.g. "worktree_add").
            args:    Extra arguments appended to the base command.
                     Each is validated by ExecutionDataFilter.

        Returns:
            ExecutionResult with returncode, stdout, stderr.

        Raises:
            ValueError:         If command is not allowlisted or an arg fails filter.
            BlockedByToolError: (caller's responsibility) — check result.success.
            asyncio.TimeoutError: If script exceeds timeout seconds.
        """
        args = args or []

        if command not in _ALLOWED_COMMANDS:
            raise ValueError(
                f"Command '{command}' is not allowlisted. "
                f"Allowed: {sorted(_ALLOWED_COMMANDS)}"
            )

        try:
            filtered  = self._filter.validate_all(args)
        except FilterError as exc:
            raise ValueError(f"Argument rejected by filter: {exc}") from exc

        clean_args = [f.value for f in filtered]
        full_cmd   = _ALLOWED_COMMANDS[command] + clean_args

        logger.info("[SafeLocalExecutor] %s", " ".join(full_cmd))

        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self._root),
        )

        try:
            raw_out, raw_err = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error("[SafeLocalExecutor] timeout after %.1fs: %s", self._timeout, command)
            raise

        stdout, truncated = _truncate(raw_out.decode(errors="replace"))
        stderr, _         = _truncate(raw_err.decode(errors="replace"))

        result = ExecutionResult(
            command=command,
            args=clean_args,
            returncode=proc.returncode or 0,
            stdout=stdout,
            stderr=stderr,
            truncated=truncated,
        )

        level = logging.INFO if result.success else logging.WARNING
        logger.log(level, "[SafeLocalExecutor] %s exit=%d", command, result.returncode)

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str) -> tuple[str, bool]:
    encoded = text.encode()
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return text, False
    cut = encoded[:_MAX_OUTPUT_BYTES].decode(errors="replace")
    return cut + "\n[... OUTPUT TRUNCATED ...]", True
