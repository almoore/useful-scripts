#!/usr/bin/env bash
# brew-migrate-x86-to-arm.sh
#
# Migrate Homebrew packages from x86_64 (/usr/local) to ARM64 (/opt/homebrew).
# For each package only in the x86 brew, installs it in ARM brew (if available),
# then optionally uninstalls it from x86 brew.
#
# Usage:
#   ./brew-migrate-x86-to-arm.sh [OPTIONS]
#
# Options:
#   -y, --yes       Auto-confirm all installs and uninstalls (non-interactive)
#   -n, --dry-run   Show what would be done without doing anything
#   --no-uninstall  Install missing packages in ARM brew but skip x86 uninstalls
#   -h, --help      Show this help

set -euo pipefail

X86_BREW="/usr/local/bin/brew"
ARM_BREW="/opt/homebrew/bin/brew"
DRY_RUN=false
AUTO_YES=false
SKIP_UNINSTALL=false

# Known deprecated/obsolete packages to skip entirely
SKIP_FORMULAE=(
  "python@2"        # EOL
  "openssl@1.1"     # deprecated, use openssl@3
  "python-flit-core" # internal build dep, not user-installed
)

# Known renamed packages: "old=new"
RENAMED_FORMULAE=(
  "kubernetes-helm=helm"
)

# Casks with no ARM equivalent or replaced by something else
SKIP_CASKS=(
  "atom"        # discontinued editor
  "android-sdk" # use android-commandlinetools cask instead
  "java8"       # use temurin@8 or openjdk@8; java8 cask is abandoned
  "wkhtmltopdf" # no ARM build; use weasyprint or chromium-based alternatives
)

#--- colors ---
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,2\}//'
  exit 0
}

confirm() {
  local prompt="$1"
  if $AUTO_YES; then return 0; fi
  read -r -p "$prompt [y/N] " response
  [[ "$response" =~ ^[Yy]$ ]]
}

in_array() {
  local needle="$1"; shift
  for item in "$@"; do [[ "$item" == "$needle" ]] && return 0; done
  return 1
}

get_rename() {
  local pkg="$1"
  for entry in "${RENAMED_FORMULAE[@]}"; do
    [[ "${entry%%=*}" == "$pkg" ]] && echo "${entry##*=}" && return
  done
  echo "$pkg"
}

install_arm_formula() {
  local pkg="$1"
  local arm_name; arm_name=$(get_rename "$pkg")
  if $DRY_RUN; then
    info "[dry-run] would install formula: $arm_name"
    return 0
  fi
  $ARM_BREW install "$arm_name" 2>&1 | tail -3
}

install_arm_cask() {
  local cask="$1"
  if $DRY_RUN; then
    info "[dry-run] would install cask: $cask"
    return 0
  fi
  $ARM_BREW install --cask "$cask" 2>&1 | tail -3
}

uninstall_x86_formula() {
  local pkg="$1"
  if $DRY_RUN; then
    info "[dry-run] would uninstall x86 formula: $pkg"
    return 0
  fi
  $X86_BREW uninstall --ignore-dependencies "$pkg" 2>&1 | tail -3
}

uninstall_x86_cask() {
  local cask="$1"
  if $DRY_RUN; then
    info "[dry-run] would uninstall x86 cask: $cask"
    return 0
  fi
  $X86_BREW uninstall --cask "$cask" 2>&1 | tail -3
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)          AUTO_YES=true ;;
    -n|--dry-run)      DRY_RUN=true ;;
    --no-uninstall)    SKIP_UNINSTALL=true ;;
    -h|--help)         usage ;;
    *) error "Unknown option: $1"; usage ;;
  esac
  shift
done

# Verify both brews exist
if [[ ! -x "$X86_BREW" ]]; then
  error "x86 Homebrew not found at $X86_BREW"
  exit 1
fi
if [[ ! -x "$ARM_BREW" ]]; then
  error "ARM Homebrew not found at $ARM_BREW"
  exit 1
fi

echo ""
info "x86 Homebrew: $X86_BREW  ($(arch -x86_64 $X86_BREW --version 2>/dev/null | head -1 || echo 'unknown version'))"
info "ARM Homebrew: $ARM_BREW  ($($ARM_BREW --version | head -1))"
echo ""
$DRY_RUN && warn "DRY RUN MODE — no changes will be made"
echo ""

#==============================================================================
# 1. Collect package lists
#==============================================================================
info "Fetching package lists..."

mapfile -t x86_formulae < <($X86_BREW list 2>/dev/null | sort)
mapfile -t arm_formulae < <($ARM_BREW list 2>/dev/null | sort)
mapfile -t x86_casks    < <($X86_BREW list --cask 2>/dev/null | sort)
mapfile -t arm_casks    < <($ARM_BREW list --cask 2>/dev/null | sort)

# Build lookup sets
declare -A arm_formula_set arm_cask_set x86_cask_set
for p in "${arm_formulae[@]}"; do arm_formula_set["$p"]=1; done
for p in "${arm_casks[@]}";    do arm_cask_set["$p"]=1; done
for p in "${x86_casks[@]}";    do x86_cask_set["$p"]=1; done

# Only-in-x86 formulae (excluding those that are also casks)
only_x86_formulae=()
for p in "${x86_formulae[@]}"; do
  if [[ -z "${arm_formula_set[$p]+_}" ]] && [[ -z "${x86_cask_set[$p]+_}" ]]; then
    only_x86_formulae+=("$p")
  fi
done

# Only-in-x86 casks
only_x86_casks=()
for p in "${x86_casks[@]}"; do
  [[ -z "${arm_cask_set[$p]+_}" ]] && only_x86_casks+=("$p")
done

echo "  x86 formulae: ${#x86_formulae[@]},  ARM formulae: ${#arm_formulae[@]}"
echo "  x86 casks:    ${#x86_casks[@]},  ARM casks:    ${#arm_casks[@]}"
echo "  x86-only formulae: ${#only_x86_formulae[@]}"
echo "  x86-only casks:    ${#only_x86_casks[@]}"
echo ""

#==============================================================================
# 2. Migrate formulae
#==============================================================================
if [[ ${#only_x86_formulae[@]} -gt 0 ]]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  info "FORMULAE — x86-only packages"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  for pkg in "${only_x86_formulae[@]}"; do
    echo ""
    if in_array "$pkg" "${SKIP_FORMULAE[@]}"; then
      warn "Skipping deprecated/obsolete formula: $pkg"
      continue
    fi

    arm_name=$(get_rename "$pkg")
    [[ "$arm_name" != "$pkg" ]] && info "Renamed: $pkg → $arm_name"

    # Check if ARM brew knows about it
    if ! $ARM_BREW info "$arm_name" &>/dev/null; then
      warn "Formula not available in ARM brew: $arm_name — skipping"
      continue
    fi

    # Already installed under different name?
    if [[ -n "${arm_formula_set[$arm_name]+_}" ]]; then
      success "$arm_name already installed in ARM brew"
    else
      if confirm "Install formula '$arm_name' in ARM brew?"; then
        install_arm_formula "$pkg" && success "Installed: $arm_name"
      fi
    fi

    if ! $SKIP_UNINSTALL && confirm "Uninstall '$pkg' from x86 brew?"; then
      uninstall_x86_formula "$pkg" && success "Uninstalled x86: $pkg"
    fi
  done
fi

#==============================================================================
# 3. Migrate casks
#==============================================================================
if [[ ${#only_x86_casks[@]} -gt 0 ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  info "CASKS — x86-only packages"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  for cask in "${only_x86_casks[@]}"; do
    echo ""
    if in_array "$cask" "${SKIP_CASKS[@]}"; then
      warn "Skipping cask (no ARM build or discontinued): $cask"
      continue
    fi

    # Check if ARM brew knows about it
    if ! $ARM_BREW info --cask "$cask" &>/dev/null; then
      warn "Cask not available in ARM brew: $cask — skipping"
      continue
    fi

    # Uninstall x86 first — its .app in /Applications blocks the ARM install
    if ! $SKIP_UNINSTALL && confirm "Uninstall cask '$cask' from x86 brew? (required before ARM install)"; then
      uninstall_x86_cask "$cask" && success "Uninstalled x86 cask: $cask"
    fi

    if confirm "Install cask '$cask' in ARM brew?"; then
      install_arm_cask "$cask" && success "Installed cask: $cask"
    fi
  done
fi

#==============================================================================
# 4. Summary
#==============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Done. Packages skipped (review manually):"
echo ""
echo "  Deprecated formulae (do not install):"
for p in "${SKIP_FORMULAE[@]}"; do echo "    - $p"; done
echo ""
echo "  Casks with no ARM equivalent (manual action needed):"
for c in "${SKIP_CASKS[@]}"; do
  case "$c" in
    atom)        echo "    - $c  → use VSCode, Zed, or another editor" ;;
    android-sdk) echo "    - $c  → use: brew install --cask android-commandlinetools" ;;
    java8)       echo "    - $c  → use: brew install --cask temurin@8" ;;
    wkhtmltopdf) echo "    - $c  → no ARM native build; use weasyprint or chromium headless" ;;
    *)           echo "    - $c" ;;
  esac
done
echo ""
