#!/usr/bin/env bash
set -euo pipefail

# Setup and manage symlinks from useful-scripts into ~/bin and ~/
#
# Usage:
#   ./setup-symlinks.sh [options] [command]
#
# Commands:
#   install   Create all symlinks (default)
#   check     Show what would be created/updated/broken (dry run)
#   remove    Remove all symlinks managed by this script
#   list      List all existing symlinks pointing to this repo
#
# Options:
#   -r, --repo-path PATH   Override repo path (default: auto-detected from script location)
#   -b, --bin-dir PATH     Override bin directory (default: ~/bin)
#   -f, --force            Overwrite existing symlinks without prompting
#   -v, --verbose          Show all operations
#   -h, --help             Show this help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="${SCRIPT_DIR}"
BIN_DIR="${HOME}/bin"
FORCE=false
VERBOSE=false
COMMAND="install"

# --- Colors ---
if [ -t 1 ]; then
  GREEN="\033[0;32m"
  YELLOW="\033[0;33m"
  RED="\033[0;31m"
  BLUE="\033[0;34m"
  BOLD="\033[1m"
  RESET="\033[0m"
else
  GREEN="" YELLOW="" RED="" BLUE="" BOLD="" RESET=""
fi

info()  { printf "${GREEN}[+]${RESET} %s\n" "$*"; }
warn()  { printf "${YELLOW}[!]${RESET} %s\n" "$*"; }
error() { printf "${RED}[-]${RESET} %s\n" "$*"; }
debug() { $VERBOSE && printf "${BLUE}[.]${RESET} %s\n" "$*" || true; }

usage() {
  sed -n '3,/^$/s/^# \?//p' "$0"
  exit 0
}

# --- Symlink manifest ---
# Format: target_relative_to_repo -> link_path
# Link paths starting with ~/ are relative to HOME
# Link paths starting with bin/ are relative to BIN_DIR

generate_manifest() {
  cat <<'MANIFEST'
# Shell dotfiles (sourced by ~/.bashrc)
bash/bash_functions.sh  ~/  .bash_functions
bash/bash-tricks.sh     ~/  .bash_tricks

# AWS
bash/aws-docker-login       bin/  aws-docker-login
aws/download-policies.sh    bin/  aws-download-policies
aws/download-roles.sh       bin/  aws-download-roles
bash/aws-ssm-find.sh        bin/  aws-ssm-find

# Git
bash/git-base.sh            bin/  git-base
bash/git-bump.sh            bin/  git-bump
python/git_jira_branch.py   bin/  git-jira-branch

# Kubernetes
k8s/check-certs                          bin/  k8s-check-certs
k8s/decode-certs.sh                      bin/  k8s-decode-certs
k8s/decode-secret.py                     bin/  k8s-decode-secrets
k8s/delete-failed-pods.sh                bin/  k8s-delete-failed-pods
k8s/delete-pods-older-than-1-day         bin/  k8s-delete-pods-older-than-1-day
k8s/k8s_filter.py                        bin/  k8s-filter
k8s/filter-all-files.sh                  bin/  k8s-filter-all-files
k8s/get_agents_yaml_ha.sh               bin/  k8s-get-agents-yaml-ha
k8s/get-events-since.sh                  bin/  k8s-get-events-since
k8s/get-failed-pods.sh                   bin/  k8s-get-failed-pods
k8s/get-latest-events.sh                 bin/  k8s-get-latest-events
k8s/get-not-running-pods.sh              bin/  k8s-get-not-running-pods
k8s/get-pod-by-node.sh                   bin/  k8s-get-pod-by-node
k8s/get-release-pods.sh                  bin/  k8s-get-release-pods
k8s/get-snapshot.sh                      bin/  k8s-get-snapshot
k8s/get-taints.sh                        bin/  k8s-get-taints
k8s/kill-kube-ns.sh                      bin/  k8s-kill-kube-ns
k8s/list-containers-go-template.sh       bin/  k8s-list-containers-go-template
k8s/list-statefulset-state-go-template.sh  bin/  k8s-list-statefulset-state-go-template
k8s/nsenter                              bin/  k8s-nsenter
k8s/setup-aws-kubeconfig.sh              bin/  k8s-setup-aws-kubeconfig
k8s/split-resources.py                   bin/  k8s-split-resources
k8s/add_kustomization_to_current         bin/  add_kustomization_to_current
k8s/add_kustomization_to_subdirs         bin/  add_kustomization_to_subdirs

# Helm
helm/hrs-values.py          bin/  hrs-values.py

# Python utilities
python/bs.py                bin/  bs
python/bs-pass.py           bin/  bs-pass
python/export_dotenv.py     bin/  export-dotenv

# Other
bash/clone_match_path       bin/  clone_match_path
bash/dockerfile-from-image  bin/  dockerfile-from-image
bash/for_each_dir.sh        bin/  for_each_dir
bash/x509-check             bin/  x509-check
MANIFEST
}

# --- Parse manifest into arrays ---
TARGETS=()
LINK_PATHS=()

parse_manifest() {
  while IFS= read -r line; do
    # Skip comments and blank lines
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Parse: target_relative  dest_prefix/  link_name
    read -r target dest_prefix link_name <<< "$line"

    local full_target="${REPO_PATH}/${target}"

    local full_link
    case "$dest_prefix" in
      "~/")  full_link="${HOME}/${link_name}" ;;
      "bin/") full_link="${BIN_DIR}/${link_name}" ;;
      *)     full_link="${dest_prefix}${link_name}" ;;
    esac

    TARGETS+=("$full_target")
    LINK_PATHS+=("$full_link")
  done < <(generate_manifest)
}

# --- Commands ---

do_check() {
  local ok=0 missing=0 wrong=0 broken=0

  for i in "${!TARGETS[@]}"; do
    local target="${TARGETS[$i]}"
    local link="${LINK_PATHS[$i]}"

    if [ ! -e "$target" ]; then
      error "Target missing: $target"
      ((broken++)) || true
    elif [ -L "$link" ]; then
      local current
      current="$(readlink "$link")"
      if [ "$current" = "$target" ]; then
        debug "OK: $link -> $target"
        ((ok++)) || true
      else
        warn "Wrong target: $link -> $current (expected $target)"
        ((wrong++)) || true
      fi
    elif [ -e "$link" ]; then
      warn "Exists but not a symlink: $link"
      ((wrong++)) || true
    else
      info "Missing: $link -> $target"
      ((missing++)) || true
    fi
  done

  # Also scan for stale symlinks pointing to useful-scripts that aren't in the manifest
  local stale=0
  while IFS= read -r link; do
    local found=false
    for managed in "${LINK_PATHS[@]}"; do
      if [ "$link" = "$managed" ]; then
        found=true
        break
      fi
    done
    if ! $found; then
      warn "Unmanaged symlink: $link -> $(readlink "$link")"
      ((stale++)) || true
    fi
  done < <(find_existing_symlinks)

  echo ""
  printf "${BOLD}Summary:${RESET} %d ok, %d missing, %d wrong, %d broken targets" "$ok" "$missing" "$wrong" "$broken"
  [ "$stale" -gt 0 ] && printf ", %d unmanaged" "$stale"
  echo ""
}

do_install() {
  # Ensure bin directory exists
  if [ ! -d "$BIN_DIR" ]; then
    info "Creating $BIN_DIR"
    mkdir -p "$BIN_DIR"
  fi

  local created=0 updated=0 skipped=0

  for i in "${!TARGETS[@]}"; do
    local target="${TARGETS[$i]}"
    local link="${LINK_PATHS[$i]}"

    if [ ! -e "$target" ]; then
      warn "Skipping (target missing): $target"
      ((skipped++)) || true
      continue
    fi

    if [ -L "$link" ]; then
      local current
      current="$(readlink "$link")"
      if [ "$current" = "$target" ]; then
        debug "Already correct: $link"
        ((skipped++)) || true
        continue
      fi
      if $FORCE; then
        ln -sfn "$target" "$link"
        info "Updated: $link -> $target (was $current)"
        ((updated++)) || true
      else
        warn "Exists with different target: $link -> $current"
        printf "  Update to %s? [y/N] " "$target"
        read -r reply
        if [[ "$reply" =~ ^[Yy] ]]; then
          ln -sfn "$target" "$link"
          info "Updated: $link"
          ((updated++)) || true
        else
          debug "Skipped: $link"
          ((skipped++)) || true
        fi
      fi
    elif [ -e "$link" ]; then
      warn "Skipping (exists, not a symlink): $link"
      ((skipped++)) || true
    else
      ln -s "$target" "$link"
      info "Created: $link -> $target"
      ((created++)) || true
    fi
  done

  echo ""
  printf "${BOLD}Done:${RESET} %d created, %d updated, %d skipped\n" "$created" "$updated" "$skipped"
}

do_remove() {
  local removed=0 skipped=0

  for i in "${!TARGETS[@]}"; do
    local target="${TARGETS[$i]}"
    local link="${LINK_PATHS[$i]}"

    if [ -L "$link" ]; then
      local current
      current="$(readlink "$link")"
      # Only remove if it points to this repo
      case "$current" in
        "${REPO_PATH}/"*)
          rm "$link"
          info "Removed: $link"
          ((removed++)) || true
          ;;
        *)
          debug "Skipping (points elsewhere): $link -> $current"
          ((skipped++)) || true
          ;;
      esac
    else
      debug "Not present: $link"
      ((skipped++)) || true
    fi
  done

  echo ""
  printf "${BOLD}Done:${RESET} %d removed, %d skipped\n" "$removed" "$skipped"
}

find_existing_symlinks() {
  # Find symlinks in ~/bin and ~/ that point to any useful-scripts path
  {
    find "$BIN_DIR" -maxdepth 1 -type l 2>/dev/null
    find "$HOME" -maxdepth 1 -type l 2>/dev/null
  } | while read -r link; do
    local target
    target="$(readlink "$link" 2>/dev/null)" || continue
    case "$target" in
      *useful-scripts*) echo "$link" ;;
    esac
  done
}

do_list() {
  echo "Existing symlinks pointing to useful-scripts:"
  echo ""

  local count=0
  while IFS= read -r link; do
    printf "  %s -> %s\n" "$link" "$(readlink "$link")"
    ((count++)) || true
  done < <(find_existing_symlinks | sort)

  echo ""
  printf "${BOLD}Total:${RESET} %d symlinks\n" "$count"
}

# --- Argument parsing ---

while [ $# -gt 0 ]; do
  case "$1" in
    -r|--repo-path) REPO_PATH="$(cd "$2" && pwd)"; shift 2 ;;
    -b|--bin-dir)   BIN_DIR="$2"; shift 2 ;;
    -f|--force)     FORCE=true; shift ;;
    -v|--verbose)   VERBOSE=true; shift ;;
    -h|--help)      usage ;;
    install|check|remove|list) COMMAND="$1"; shift ;;
    *) error "Unknown argument: $1"; usage ;;
  esac
done

parse_manifest

case "$COMMAND" in
  install) do_install ;;
  check)   do_check ;;
  remove)  do_remove ;;
  list)    do_list ;;
esac
