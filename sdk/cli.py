"""sdk/cli.py — CLI entry point for the `piv` / `piv-oac` command.

Commands:
    piv init --provider=<anthropic|openai|ollama>
    piv validate
    piv run --provider=<provider> --objective="..."
    piv test
    piv test:unit
    piv test:int
    piv lint
    piv observe:start | observe:stop | observe:logs

Thin wrapper: all heavyweight logic lives in sys/bootstrap.sh and sdk/.
This file translates CLI args into SDK calls and shell delegations.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Walk up from cwd to find the repo root (contains pyproject.toml or .git)."""
    here = Path.cwd()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return here


def _run_bootstrap(command: str, repo: Path) -> int:
    """Delegate to sys/bootstrap.sh for shell-level operations."""
    script = repo / "sys" / "bootstrap.sh"
    if not script.exists():
        print(f"[piv] Error: sys/bootstrap.sh not found at {script}", file=sys.stderr)
        return 1
    result = subprocess.run(["bash", str(script), command], cwd=str(repo))
    return result.returncode


def cmd_init(args: argparse.Namespace, repo: Path) -> int:
    """piv init — workspace bootstrap."""
    from sdk.core.init import Initializer, InitError

    provider = getattr(args, "provider", "anthropic")
    try:
        init = Initializer(repo_root=repo, provider=provider)
        result = init.run()
        print(f"[piv] init complete ({result.case})")
        for branch in result.branches_created:
            print(f"  + created branch: {branch}")
        for warning in result.warnings:
            print(f"  ! warning: {warning}")
        print(f"  session_id: {result.session_id}")
        return 0
    except InitError as exc:
        print(f"[piv] init failed: {exc}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace, repo: Path) -> int:
    """piv validate — run sys/_verify.md checks via bootstrap.sh."""
    return _run_bootstrap("validate", repo)


def cmd_run(args: argparse.Namespace, repo: Path) -> int:
    """piv run — start a PIV/OAC session."""
    from sdk import Session

    provider  = getattr(args, "provider", "anthropic")
    objective = getattr(args, "objective", "")
    local_model = getattr(args, "local_model", None)

    if not objective:
        print("[piv] Error: --objective is required for 'run'", file=sys.stderr)
        return 1

    result = Session.init(
        provider=provider,
        local_model=local_model,
        repo_root=repo,
    ).run(objective=objective)

    print(f"[piv] session started: {result['session_id']}")
    print(f"  complexity: Level {result['complexity']}")
    print(f"  fast_track: {result['fast_track']}")
    return 0


def cmd_lint(args: argparse.Namespace, repo: Path) -> int:
    return _run_bootstrap("lint", repo)


def cmd_test(args: argparse.Namespace, repo: Path) -> int:
    return _run_bootstrap("test", repo)


def cmd_test_unit(args: argparse.Namespace, repo: Path) -> int:
    return _run_bootstrap("test:unit", repo)


def cmd_test_int(args: argparse.Namespace, repo: Path) -> int:
    return _run_bootstrap("test:int", repo)


def cmd_observe(args: argparse.Namespace, repo: Path) -> int:
    subcmd = getattr(args, "subcmd", "start")
    return _run_bootstrap(f"observe:{subcmd}", repo)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piv",
        description="PIV/OAC v5.0 — Verifiable Intentionality Orchestration",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Bootstrap workspace and branch structure")
    p_init.add_argument("--provider", default="anthropic",
                        choices=["anthropic", "openai", "ollama"])

    # validate
    sub.add_parser("validate", help="Run sys/_verify.md preflight checks")

    # run
    p_run = sub.add_parser("run", help="Start a PIV/OAC session")
    p_run.add_argument("--provider", default="anthropic",
                       choices=["anthropic", "openai", "ollama"])
    p_run.add_argument("--objective", required=True, help="Session objective")
    p_run.add_argument("--local-model", dest="local_model", default=None,
                       help="Ollama model tag for Tier 2 (e.g. llama3.2:1b)")

    # lint / test
    sub.add_parser("lint", help="Run ruff check + format check")
    sub.add_parser("test", help="Run all tests")
    sub.add_parser("test:unit", help="Run unit tests only")
    sub.add_parser("test:int", help="Run integration tests only")

    # observe
    p_obs = sub.add_parser("observe", help="Manage Grafana observability stack")
    p_obs.add_argument("subcmd", choices=["start", "stop", "logs"])

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    repo = _repo_root()

    dispatch = {
        "init":      cmd_init,
        "validate":  cmd_validate,
        "run":       cmd_run,
        "lint":      cmd_lint,
        "test":      cmd_test,
        "test:unit": cmd_test_unit,
        "test:int":  cmd_test_int,
        "observe":   cmd_observe,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(0)

    sys.exit(handler(args, repo))


if __name__ == "__main__":
    main()
