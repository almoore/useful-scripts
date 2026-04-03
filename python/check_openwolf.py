#!/usr/bin/env python3
"""
Check if OpenWolf is installed and enabled in all Claude-configured repos.

Discovers repos by finding CLAUDE.md files under a base path, then runs
'openwolf status' in each to verify initialization.

Usage:
  check_openwolf.py [--path DIR] [--init] [--dry-run] [--ask]
                    [--exclude PATH] [--json] [--quiet]

Examples:
  check_openwolf.py
  check_openwolf.py --path ~/work/repos
  check_openwolf.py --init --ask
  check_openwolf.py --init --dry-run
  check_openwolf.py --json
  check_openwolf.py --exclude ~/repos/github.com/almoore/proxmox
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_install(quiet: bool) -> bool:
    """Verify openwolf is installed, attempt npm install if not. Returns True if available."""
    if shutil.which("openwolf"):
        if not quiet:
            print(f"✓ openwolf installed: {shutil.which('openwolf')}")
        return True

    print("✗ openwolf not found in PATH", file=sys.stderr)

    if not shutil.which("npm"):
        print("  npm not found — cannot install openwolf automatically", file=sys.stderr)
        print("  Install manually: npm install -g openwolf", file=sys.stderr)
        return False

    print("  Installing openwolf via npm...", file=sys.stderr)
    result = subprocess.run(["npm", "install", "-g", "openwolf"])
    if result.returncode == 0:
        print("✓ openwolf installed successfully")
        return True
    else:
        print("✗ Failed to install openwolf", file=sys.stderr)
        return False


def find_repos(base_path: Path, excludes: list[str]) -> list[Path]:
    """Find all repo directories containing CLAUDE.md under base_path."""
    repos = []
    for claude_file in sorted(base_path.rglob("CLAUDE.md")):
        # Limit depth to 5 levels
        try:
            relative = claude_file.relative_to(base_path)
            if len(relative.parts) > 6:  # CLAUDE.md itself is 1 part
                continue
        except ValueError:
            continue

        repo_dir = claude_file.parent
        repo_str = str(repo_dir)

        excluded = any(repo_str.startswith(str(Path(e).expanduser())) for e in excludes)
        repos.append((repo_dir, excluded))

    return repos


def check_repo(repo_dir: Path) -> dict:
    """Check if a repo has OpenWolf initialized, return result dict.

    Note: openwolf status exits 0 even when not initialized, so we check
    for .wolf/OPENWOLF.md presence as the initialization indicator.
    """
    initialized = (repo_dir / ".wolf" / "OPENWOLF.md").exists()
    status = "healthy"

    if initialized:
        result = subprocess.run(
            ["openwolf", "status"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        # Check if status output indicates an issue despite OPENWOLF.md existing
        if "error" in (result.stdout + result.stderr).lower():
            status = "error"
    else:
        status = "run: openwolf init"

    return {
        "path": str(repo_dir),
        "initialized": initialized,
        "status": status,
    }


def run_init(repo_dir: Path, dry_run: bool, ask: bool, quiet: bool) -> bool:
    """Run openwolf init in a repo. Returns True if init was performed."""
    if dry_run:
        if not quiet:
            print(f"  [dry-run] would run: openwolf init in {repo_dir}")
        return False

    if ask:
        answer = input(f"  Initialize OpenWolf in {repo_dir}? [y/N] ")
        if not answer.lower().startswith("y"):
            return False

    if not quiet:
        print(f"  Running: openwolf init in {repo_dir}")
    result = subprocess.run(["openwolf", "init"], cwd=repo_dir)
    return result.returncode == 0


def print_table(results: list[dict]) -> None:
    col_repo = 55
    col_status = 14

    print()
    print(f"{'REPO':<{col_repo}}  {'OPENWOLF':<{col_status}}  STATUS")
    print(f"{'-' * col_repo}  {'-' * col_status}  {'-' * 20}")

    for r in results:
        path = r["path"]
        if r.get("excluded"):
            ow_col = "excluded"
            status_col = "(skipped)"
        elif r["initialized"]:
            ow_col = "✓ initialized"
            status_col = "healthy"
        else:
            ow_col = "✗ not init"
            status_col = r["status"]

        print(f"{path:<{col_repo}}  {ow_col:<{col_status}}  {status_col}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check if OpenWolf is installed and enabled in all Claude-configured repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-p", "--path",
        default=str(Path.home() / "repos"),
        metavar="DIR",
        help="Base search path (default: ~/repos)",
    )
    parser.add_argument(
        "-i", "--init",
        action="store_true",
        help="Run 'openwolf init' on uninitialized repos",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show what would be done without making changes (use with --init)",
    )
    parser.add_argument(
        "-a", "--ask",
        action="store_true",
        help="Prompt before initializing each repo (use with --init)",
    )
    parser.add_argument(
        "-e", "--exclude",
        action="append",
        default=[],
        metavar="PATH",
        help="Exclude a path prefix (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all output except errors; exit 1 if any failures",
    )
    args = parser.parse_args()

    # Install check
    if not check_install(args.quiet):
        return 1

    base_path = Path(args.path).expanduser().resolve()
    if not base_path.is_dir():
        print(f"✗ Path not found: {base_path}", file=sys.stderr)
        return 1

    repos = find_repos(base_path, args.exclude)

    if not repos:
        if not args.quiet:
            print(f"No CLAUDE.md files found under {base_path}")
        return 0

    results = []
    uninit_repos = []

    for repo_dir, excluded in repos:
        if excluded:
            results.append({"path": str(repo_dir), "initialized": None, "status": "excluded", "excluded": True})
            continue

        r = check_repo(repo_dir)
        results.append(r)
        if not r["initialized"]:
            uninit_repos.append(repo_dir)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    elif not args.quiet:
        print_table(results)
        total = sum(1 for r in results if not r.get("excluded"))
        initialized = sum(1 for r in results if r.get("initialized") is True)
        print(f"\nSummary: {initialized}/{total} repos initialized")

    # Handle --init
    if args.init and uninit_repos:
        if not args.quiet:
            print(f"\nInitializing {len(uninit_repos)} repo(s)...")
        for repo_dir in uninit_repos:
            run_init(repo_dir, args.dry_run, args.ask, args.quiet)

    # Exit code
    if uninit_repos:
        if args.init and not args.dry_run and not args.ask:
            return 0
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
