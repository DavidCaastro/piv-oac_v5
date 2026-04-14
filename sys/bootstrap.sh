#!/usr/bin/env bash
# sys/bootstrap.sh — PIV/OAC v5.0 command runner
# Implements sys/_verify.md checks and exposes all agent-requestable operations.
# Usage: bash sys/bootstrap.sh <command>

set -euo pipefail

PIV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load .env if present — never committed, holds local secrets and defaults.
# Variables already in the environment take precedence (set -a exports sourced vars).
if [ -f "${PIV_ROOT}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${PIV_ROOT}/.env"
  set +a
fi

# Defaults — applied after .env so explicit values win.
PIV_SESSION_DIR="${PIV_SESSION_DIR:-.piv}"
PIV_VAULT_PATH="${PIV_VAULT_PATH:-.piv/vault}"
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"

# ─────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────
RED='\033[0;31m'
YEL='\033[0;33m'
GRN='\033[0;32m'
NC='\033[0m'

pass()  { printf "  %-48s ${GRN}PASS${NC}\n" "$1"; }
warn()  { printf "  %-48s ${YEL}WARN${NC}\n" "$1"; }
fail()  { printf "  %-48s ${RED}FAIL${NC}\n" "$1"; }
block() { echo -e "${RED}BLOCKER: $1${NC}"; exit 1; }

# ─────────────────────────────────────────────
# COMMAND: validate
# Runs all 8 checks from sys/_verify.md
# ─────────────────────────────────────────────
cmd_validate() {
  echo "[PIV/OAC] Pre-flight verification"
  echo ""
  local exit_code=0

  # CHECK 1 — venv active
  if python --version 2>&1 | grep -qE "3\.(1[1-9]|[2-9][0-9])"; then
    PY_VER=$(python --version 2>&1)
    pass "CHECK 1  venv active ($PY_VER)"
  else
    fail "CHECK 1  venv active"
    echo "         Run: bash sys/bootstrap.sh setup"
    exit_code=1
  fi

  # CHECK 2 — git remote reachable
  if GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code origin HEAD &>/dev/null; then
    pass "CHECK 2  git remote reachable"
  else
    fail "CHECK 2  git remote reachable"
    exit_code=1
  fi

  # CHECK 3 — git credentials valid (same command, different failure mode)
  if GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code origin HEAD &>/dev/null; then
    pass "CHECK 3  git credentials valid"
  else
    fail "CHECK 3  git credentials valid"
    exit_code=1
  fi

  # CHECK 4 — required env vars (PIV_SESSION_DIR + PIV_VAULT_PATH have defaults)
  local missing=0
  for var in PIV_PROVIDER; do
    if [ -z "${!var:-}" ]; then
      fail "CHECK 4  env var $var missing (set in .env or export)"
      missing=$((missing + 1))
      exit_code=1
    fi
  done
  if [ "$missing" -eq 0 ]; then
    pass "CHECK 4  env vars present (PIV_PROVIDER=${PIV_PROVIDER} SESSION_DIR=${PIV_SESSION_DIR} VAULT=${PIV_VAULT_PATH})"
  fi

  # CHECK 5 — provider token
  local provider="${PIV_PROVIDER:-}"
  case "$provider" in
    anthropic)
      if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        pass "CHECK 5  provider token present (anthropic)"
      else
        fail "CHECK 5  provider token missing (ANTHROPIC_API_KEY)"; exit_code=1
      fi ;;
    openai)
      if [ -n "${OPENAI_API_KEY:-}" ]; then
        pass "CHECK 5  provider token present (openai)"
      else
        fail "CHECK 5  provider token missing (OPENAI_API_KEY)"; exit_code=1
      fi ;;
    ollama)
      if curl -sf "http://${OLLAMA_HOST}:11434/api/tags" &>/dev/null; then
        pass "CHECK 5  provider reachable (ollama @ ${OLLAMA_HOST})"
      else
        fail "CHECK 5  ollama unreachable (${OLLAMA_HOST}:11434)"; exit_code=1
      fi ;;
    "")
      fail "CHECK 5  PIV_PROVIDER not set"; exit_code=1 ;;
    *)
      fail "CHECK 5  unknown provider: $provider"; exit_code=1 ;;
  esac

  # CHECK 6 — skills manifest SHA-256
  local manifest="${PIV_ROOT}/skills/manifest.json"
  local versioning="${PIV_ROOT}/engram/VERSIONING.md"
  if [ ! -f "$manifest" ]; then
    warn "CHECK 6  skills/manifest.json not found (build pending)"
  else
    local actual
    actual=$(sha256sum "$manifest" | awk '{print $1}')
    # grep exits 1 when entry is absent — || true prevents set -e from aborting
    local expected
    expected=$(grep -A1 "skills-manifest" "$versioning" 2>/dev/null | tail -1 | awk '{print $1}' || true)
    if [ -z "$expected" ]; then
      # First run or baseline not yet written — establish it now
      warn "CHECK 6  skills manifest — no baseline yet, establishing now"
      mkdir -p "${PIV_ROOT}/.piv"
      {
        echo ""
        echo "## skills-manifest"
        echo "${actual}  skills/manifest.json"
      } >> "$versioning"
      pass "CHECK 6  skills manifest SHA-256 (baseline written to VERSIONING.md)"
    elif [ "$expected" = "$actual" ]; then
      pass "CHECK 6  skills manifest SHA-256"
    else
      fail "CHECK 6  skills manifest hash MISMATCH — possible tampering"
      mkdir -p "${PIV_ROOT}/.piv/alerts"
      echo "CROSS_ALERT: skills manifest hash mismatch at $(date -u +%FT%TZ)" \
        >> "${PIV_ROOT}/.piv/alerts/security_alert_$(date +%s).log"
      exit_code=1
    fi
  fi

  # CHECK 7 — session state (WARNING only)
  if ls "${PIV_ROOT}/${PIV_SESSION_DIR}/active/"*.json &>/dev/null 2>&1; then
    local session_ids
    session_ids=$(ls "${PIV_ROOT}/${PIV_SESSION_DIR}/active/"*.json 2>/dev/null | xargs -I{} basename {} .json)
    warn "CHECK 7  unclosed session(s) in .piv/active/"
    echo "         $session_ids"
    echo "         Run: piv-oac resume OR piv-oac discard"
  else
    pass "CHECK 7  session state (no unclosed sessions)"
  fi

  # CHECK 8 — stale worktrees (WARNING only)
  if [ -d "${PIV_ROOT}/worktrees" ]; then
    local stale
    stale=$(comm -23 \
      <(ls "${PIV_ROOT}/worktrees/" 2>/dev/null | sort) \
      <(git worktree list --porcelain 2>/dev/null | grep "^worktree" | awk '{print $2}' | xargs -I{} basename {} | sort) \
      2>/dev/null || true)
    if [ -n "$stale" ]; then
      warn "CHECK 8  stale worktrees detected"
      echo "         Run: piv wt:prune"
    else
      pass "CHECK 8  stale worktrees (none found)"
    fi
  else
    pass "CHECK 8  stale worktrees (worktrees/ not yet created)"
  fi

  echo ""
  echo "  ──────────────────────────────────────────────────────"
  if [ "$exit_code" -eq 0 ]; then
    echo -e "  ${GRN}All checks passed. Routing to sdk/.${NC}"
  else
    echo -e "  ${RED}One or more BLOCKER checks failed. Fix above errors and retry.${NC}"
  fi
  return "$exit_code"
}

# ─────────────────────────────────────────────
# COMMAND: setup
# Creates venv, installs deps, then validates
# ─────────────────────────────────────────────
cmd_setup() {
  echo "[PIV/OAC] Environment setup"
  python3 -m venv "${PIV_ROOT}/.venv"
  source "${PIV_ROOT}/.venv/bin/activate"
  pip install --upgrade pip -q
  pip install -e "${PIV_ROOT}[dev]" -q
  echo "Setup complete."
  cmd_validate
}

# ─────────────────────────────────────────────
# COMMAND: test
# ─────────────────────────────────────────────
cmd_test()      { pytest "${PIV_ROOT}/tests/" -v "$@"; }
cmd_test_unit() { pytest "${PIV_ROOT}/tests/" -v -m unit "$@"; }
cmd_test_int()  { pytest "${PIV_ROOT}/tests/" -v -m integration "$@"; }

# ─────────────────────────────────────────────
# COMMAND: lint
# ─────────────────────────────────────────────
cmd_lint() {
  ruff check "${PIV_ROOT}/sdk/" "${PIV_ROOT}/tests/"
  ruff format --check "${PIV_ROOT}/sdk/" "${PIV_ROOT}/tests/"
}

# ─────────────────────────────────────────────
# COMMANDS: worktrees
# ─────────────────────────────────────────────
cmd_wt_add() {
  local task="${1:?Usage: piv wt:add <task-id> <expert-N>}"
  local expert="${2:?Usage: piv wt:add <task-id> <expert-N>}"
  local path="${PIV_ROOT}/worktrees/${task}/${expert}"
  local branch="feature/${task}/${expert}"
  git worktree add "$path" -b "$branch"
  echo "Worktree created: $path (branch: $branch)"
}
cmd_wt_list()   { git worktree list; }
cmd_wt_remove() {
  local path="${1:?Usage: piv wt:remove <path>}"
  local branch
  branch=$(git worktree list --porcelain | grep -A2 "worktree $path" | grep "branch" | awk '{print $2}')
  git worktree remove "$path"
  [ -n "$branch" ] && git branch -d "$branch" && echo "Branch deleted: $branch"
}
cmd_wt_prune()  { git worktree prune; echo "Stale worktree references pruned."; }

# ─────────────────────────────────────────────
# COMMANDS: observability
# ─────────────────────────────────────────────
cmd_observe_start() {
  docker compose -f "${PIV_ROOT}/observability/docker-compose.yml" up -d
  echo "Observability stack started. Grafana: http://localhost:3000"
}
cmd_observe_stop() {
  docker compose -f "${PIV_ROOT}/observability/docker-compose.yml" down
}
cmd_observe_logs() {
  local latest
  latest=$(ls -t "${PIV_ROOT}/logs/sessions/"*.jsonl 2>/dev/null | head -1)
  [ -z "$latest" ] && echo "No session logs found." && exit 0
  tail -f "$latest"
}

# ─────────────────────────────────────────────
# COMMAND: run
# ─────────────────────────────────────────────
cmd_run() { python -m sdk.cli "$@"; }

# ─────────────────────────────────────────────
# DISPATCH
# ─────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  validate)       cmd_validate ;;
  setup)          cmd_setup ;;
  test)           cmd_test "$@" ;;
  test:unit)      cmd_test_unit "$@" ;;
  test:int)       cmd_test_int "$@" ;;
  lint)           cmd_lint ;;
  wt:add)         cmd_wt_add "$@" ;;
  wt:list)        cmd_wt_list ;;
  wt:remove)      cmd_wt_remove "$@" ;;
  wt:prune)       cmd_wt_prune ;;
  observe:start)  cmd_observe_start ;;
  observe:stop)   cmd_observe_stop ;;
  observe:logs)   cmd_observe_logs ;;
  run)            cmd_run "$@" ;;
  help|*)
    echo "Usage: bash sys/bootstrap.sh <command>"
    echo ""
    echo "Verification"
    echo "  validate          Run all 8 pre-flight checks (sys/_verify.md)"
    echo "  setup             Create venv + install deps + validate"
    echo ""
    echo "Development"
    echo "  test              pytest tests/ -v"
    echo "  test:unit         pytest tests/ -v -m unit"
    echo "  test:int          pytest tests/ -v -m integration"
    echo "  lint              ruff check + ruff format --check"
    echo ""
    echo "Worktrees"
    echo "  wt:add <task> <expert>    Create worktree for feature/<task>/<expert>"
    echo "  wt:list                   List all active worktrees"
    echo "  wt:remove <path>          Remove worktree + delete branch"
    echo "  wt:prune                  Prune stale worktree references"
    echo ""
    echo "Observability"
    echo "  observe:start     Start Grafana + Loki + Tempo + OTEL stack"
    echo "  observe:stop      Stop observability stack"
    echo "  observe:logs      Tail latest session log file"
    echo ""
    echo "Runtime"
    echo "  run               python -m sdk.cli (Phase 2+)"
    ;;
esac
