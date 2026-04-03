#!/usr/bin/env bash
set -euo pipefail

#---  FUNCTION  -----------------------------------------------------------
#          NAME:  Usage
#   DESCRIPTION:  Display usage information
#----------------------------------------------------------------------
Usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Check if OpenWolf is installed and enabled in all Claude-configured repos.

Options:
  -p, --path DIR       Base search path (default: ~/repos)
  -i, --init           Run 'openwolf init' on uninitialized repos
  -n, --dry-run        Show what would be done without making changes (use with --init)
  -a, --ask            Prompt before initializing each repo (use with --init)
  -e, --exclude PATH   Exclude a path prefix (repeatable)
  -q, --quiet          Suppress all output except errors; exit 1 if any failures
  -h, --help           Show this help message

Exit codes:
  0  All repos healthy (OpenWolf initialized)
  1  One or more repos not initialized, or OpenWolf not installed

Examples:
  $(basename "$0")
  $(basename "$0") --path ~/work/repos
  $(basename "$0") --init --ask
  $(basename "$0") --init --dry-run
  $(basename "$0") --exclude ~/repos/github.com/almoore/proxmox
EOF
}

#---  FUNCTION  -----------------------------------------------------------
#          NAME:  check_install
#   DESCRIPTION:  Verify openwolf is installed, attempt npm install if not
#----------------------------------------------------------------------
check_install() {
  if command -v openwolf &>/dev/null; then
    [[ "$QUIET" == "false" ]] && echo "✓ openwolf installed: $(command -v openwolf)"
    return 0
  fi

  echo "✗ openwolf not found in PATH" >&2

  if ! command -v npm &>/dev/null; then
    echo "  npm not found — cannot install openwolf automatically" >&2
    echo "  Install manually: npm install -g openwolf" >&2
    exit 1
  fi

  echo "  Installing openwolf via npm..." >&2
  if npm install -g openwolf; then
    echo "✓ openwolf installed successfully"
  else
    echo "✗ Failed to install openwolf" >&2
    exit 1
  fi
}

#---  FUNCTION  -----------------------------------------------------------
#          NAME:  is_excluded
#   DESCRIPTION:  Check if a path matches any exclude prefix
#----------------------------------------------------------------------
is_excluded() {
  local repo_path="$1"
  local exc
  for exc in "${EXCLUDES[@]}"; do
    # Expand ~ in exclude paths
    exc="${exc/#\~/$HOME}"
    if [[ "$repo_path" == "$exc"* ]]; then
      return 0
    fi
  done
  return 1
}

#---  FUNCTION  -----------------------------------------------------------
#          NAME:  run_init
#   DESCRIPTION:  Run openwolf init in a repo directory
#----------------------------------------------------------------------
run_init() {
  local repo_dir="$1"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  [dry-run] would run: openwolf init in $repo_dir"
    return 0
  fi

  if [[ "$ASK" == "true" ]]; then
    read -r -p "  Initialize OpenWolf in $repo_dir? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || return 0
  fi

  echo "  Running: openwolf init in $repo_dir"
  (cd "$repo_dir" && openwolf init)
}

#---  VARIABLES  ----------------------------------------------------------
BASE_PATH="$HOME/repos"
DO_INIT="false"
DRY_RUN="false"
ASK="false"
QUIET="false"
EXCLUDES=()

#---  ARGUMENT PARSING  ---------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--path)
      BASE_PATH="${2:?--path requires a directory argument}"
      shift 2 ;;
    -i|--init)
      DO_INIT="true"
      shift ;;
    -n|--dry-run)
      DRY_RUN="true"
      shift ;;
    -a|--ask)
      ASK="true"
      shift ;;
    -e|--exclude)
      EXCLUDES+=("${2:?--exclude requires a path argument}")
      shift 2 ;;
    -q|--quiet)
      QUIET="true"
      shift ;;
    -h|--help)
      Usage
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      Usage >&2
      exit 1 ;;
  esac
done

# Expand ~ in BASE_PATH
BASE_PATH="${BASE_PATH/#\~/$HOME}"

#---  MAIN  ---------------------------------------------------------------
check_install

# Collect all CLAUDE.md repos
mapfile -t CLAUDE_FILES < <(find "$BASE_PATH" -maxdepth 5 -name "CLAUDE.md" 2>/dev/null | sort)

if [[ ${#CLAUDE_FILES[@]} -eq 0 ]]; then
  [[ "$QUIET" == "false" ]] && echo "No CLAUDE.md files found under $BASE_PATH"
  exit 0
fi

# Column widths
COL_REPO=55
COL_STATUS=14

# Header
if [[ "$QUIET" == "false" ]]; then
  echo ""
  printf "%-${COL_REPO}s  %-${COL_STATUS}s  %s\n" "REPO" "OPENWOLF" "STATUS"
  printf "%-${COL_REPO}s  %-${COL_STATUS}s  %s\n" "$(printf '%0.s-' {1..55})" "$(printf '%0.s-' {1..14})" "$(printf '%0.s-' {1..20})"
fi

FAIL_COUNT=0
UNINIT_REPOS=()

for claude_file in "${CLAUDE_FILES[@]}"; do
  repo_dir="$(dirname "$claude_file")"

  if is_excluded "$repo_dir"; then
    [[ "$QUIET" == "false" ]] && printf "%-${COL_REPO}s  %-${COL_STATUS}s  %s\n" "$repo_dir" "excluded" "(skipped)"
    continue
  fi

  # Check initialization via .wolf/OPENWOLF.md presence
  # (openwolf status exits 0 even when not initialized)
  if [[ -f "$repo_dir/.wolf/OPENWOLF.md" ]]; then
    status_output=$(cd "$repo_dir" && openwolf status 2>&1 | head -1)
    [[ "$QUIET" == "false" ]] && printf "%-${COL_REPO}s  %-${COL_STATUS}s  %s\n" "$repo_dir" "✓ initialized" "healthy"
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    UNINIT_REPOS+=("$repo_dir")
    if [[ "$QUIET" == "false" ]]; then
      printf "%-${COL_REPO}s  %-${COL_STATUS}s  %s\n" "$repo_dir" "✗ not init" "run: openwolf init"
    fi
  fi
done

# Summary
if [[ "$QUIET" == "false" ]]; then
  echo ""
  total=${#CLAUDE_FILES[@]}
  initialized=$((total - FAIL_COUNT))
  echo "Summary: $initialized/$total repos initialized"
fi

# Handle --init
if [[ "$DO_INIT" == "true" && ${#UNINIT_REPOS[@]} -gt 0 ]]; then
  if [[ "$QUIET" == "false" ]]; then
    echo ""
    echo "Initializing ${#UNINIT_REPOS[@]} repo(s)..."
  fi
  for repo_dir in "${UNINIT_REPOS[@]}"; do
    run_init "$repo_dir"
  done
fi

# Exit 1 if any failures remain (or would remain after dry-run)
if [[ "$FAIL_COUNT" -gt 0 ]]; then
  if [[ "$DO_INIT" == "true" && "$DRY_RUN" == "false" && "$ASK" == "false" ]]; then
    exit 0
  fi
  exit 1
fi

exit 0
