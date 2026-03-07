#!/usr/bin/env python3
"""Review Atlantis plan output from a GitHub PR.

Fetches the latest Atlantis plan comment from a PR, parses resource counts,
flags destroys or errors, and prints a concise summary.

Requires: gh CLI (authenticated)

Usage:
    atlantis-review.py 7221
    atlantis-review.py https://github.com/grindrllc/infra-terraform/pull/7221
    atlantis-review.py                # lists open PRs
"""

import argparse
import json
import re
import subprocess
import sys


def run_gh(args: list[str]) -> str:
    """Run a gh CLI command and return stdout."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        print(f"Error: gh {' '.join(args[:3])}... timed out after 30s", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"Error running gh {' '.join(args)}:", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def extract_pr_number(arg: str) -> int | None:
    """Extract PR number from a number string or GitHub URL."""
    if arg.isdigit():
        return int(arg)
    m = re.search(r'/pull/(\d+)', arg)
    if m:
        return int(m.group(1))
    return None


def get_pr_details(pr_number: int, repo: str) -> dict:
    """Fetch PR metadata."""
    out = run_gh([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "title,headRefName,baseRefName,state,files",
    ])
    return json.loads(out)


def get_pr_comments(pr_number: int, repo: str) -> list[dict]:
    """Fetch all issue comments on a PR as separate objects."""
    out = run_gh([
        "api", f"repos/{repo}/issues/{pr_number}/comments",
        "--jq", "[.[] | {body: .body}]",
    ])
    return json.loads(out) if out else []


def find_atlantis_comments(comments: list[dict]) -> list[str]:
    """Filter and reassemble Atlantis plan comments, including continuations.

    Atlantis splits long plan output across multiple comments:
    - First comment starts with 'Ran Plan for ...'
    - Continuation comments start with 'Continued plan output from previous comment.'
    Continuations are concatenated back onto their parent comment.
    """
    atlantis = []
    for comment in comments:
        body = comment.get("body", "")
        if body.startswith("Ran Plan for"):
            atlantis.append(body)
        elif body.startswith("Continued plan output") and atlantis:
            atlantis[-1] += "\n" + body
    return atlantis


def parse_plan(comment: str) -> dict:
    """Parse an Atlantis plan comment into structured data."""
    result = {
        "raw": comment,
        "project": None,
        "directory": None,
        "status": "unknown",
        "adds": 0,
        "changes": 0,
        "destroys": 0,
        "lock_conflict": None,
        "error": None,
        "warnings": [],
        "destroyed_resources": [],
        "changed_resources": [],
        "created_resources": [],
        "resource_details": {},  # resource_name -> list of key attribute changes
    }

    # Extract project/directory
    m = re.search(r'project:\s*`([^`]+)`', comment)
    if m:
        result["project"] = m.group(1)
    m = re.search(r'dir:\s*`([^`]+)`', comment)
    if m:
        result["directory"] = m.group(1)

    # Check for lock conflict
    m = re.search(r'\*\*Plan Failed\*\*.*locked by.*pull #(\d+)', comment)
    if m:
        result["status"] = "locked"
        result["lock_conflict"] = int(m.group(1))
        return result

    # Check for plan error
    if "**Plan Error**" in comment or "**Plan Failed**" in comment:
        result["status"] = "failed"
        # Try to extract error message
        m = re.search(r'```\n(.*?)\n```', comment, re.DOTALL)
        if m:
            result["error"] = m.group(1).strip()[:500]
        return result

    # Extract plan counts
    m = re.search(r'Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy', comment)
    if m:
        result["adds"] = int(m.group(1))
        result["changes"] = int(m.group(2))
        result["destroys"] = int(m.group(3))
        result["status"] = "planned"

    # Check run status
    if "planned and saved" in comment:
        result["status"] = "planned"
    elif "No changes" in comment or "0 to add, 0 to change, 0 to destroy" in comment:
        result["status"] = "no_changes"

    # Extract resource names from all diff blocks (may span continuation comments)
    diff_blocks = re.findall(r'```diff\n(.*?)\n```', comment, re.DOTALL)
    diff_block = "\n".join(diff_blocks)

    # Resource action pattern — Terraform plan uses '# resource.name will be ...'
    # Use \S+ since resource names contain hyphens, dots, brackets, quotes
    res_pattern = r'#\s+(\S+)\s+will be'

    # Resources being destroyed (deduplicated, preserving order)
    seen = set()
    for rm in re.finditer(res_pattern + r' destroyed', diff_block):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["destroyed_resources"].append(name)

    # Resources being created
    seen = set()
    for rm in re.finditer(res_pattern + r' created', diff_block):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["created_resources"].append(name)

    # Resources being updated
    seen = set()
    for rm in re.finditer(res_pattern + r' updated in-place', diff_block):
        name = rm.group(1)
        if name not in seen:
            seen.add(name)
            result["changed_resources"].append(name)

    # Extract key attribute changes per resource
    # Split diff block into per-resource sections on the '# resource will be' lines
    resource_sections = re.split(r'(?=\n\s*#\s+\S+\s+will be )', diff_block)
    for section in resource_sections:
        rm = re.search(r'#\s+(\S+)\s+will be (\w+)', section)
        if not rm:
            continue
        res_name = rm.group(1)
        details = []

        # For created resources, extract key attributes
        if "will be created" in section:
            for attr_m in re.finditer(
                r'\+\s+(instance_class|engine|engine_version|node_type|'
                r'instance_type|cluster_identifier|identifier)\s+'
                r'=\s+"?([^"\n]+)"?',
                section,
            ):
                details.append(f"{attr_m.group(1)} = {attr_m.group(2).strip()}")

        # For updated resources, extract changed attributes (! lines)
        if "will be updated" in section:
            for attr_m in re.finditer(
                r'!\s+(\w+)\s+=\s+(.+)',
                section,
            ):
                attr_name = attr_m.group(1).strip()
                attr_value = attr_m.group(2).strip()
                details.append(f"{attr_name}: {attr_value}")

        if details and res_name not in result["resource_details"]:
            result["resource_details"][res_name] = details

    # Warnings
    for wm in re.finditer(r'Warning:\s*(.+)', comment):
        w = wm.group(1).strip()
        if w not in result["warnings"]:
            result["warnings"].append(w)

    return result


def print_review(pr: dict, plans: list[dict]):
    """Print the formatted review."""
    title = pr.get("title", "Unknown")
    head = pr.get("headRefName", "?")
    base = pr.get("baseRefName", "?")

    print(f"## PR — {title}")
    print(f"Branch: {head} -> {base}")
    print()

    if not plans:
        print("### No Atlantis plan found")
        print("No Atlantis plan comments found on this PR.")
        return

    for plan in plans:
        project = plan["project"] or plan["directory"] or "default"
        print(f"### Project: {project}")
        print()

        # Status
        if plan["status"] == "locked":
            print(f"**Status: LOCKED** by PR #{plan['lock_conflict']}")
            print(f"Resolve by applying/closing PR #{plan['lock_conflict']} or running `atlantis unlock` on that PR.")
            print()
            continue

        if plan["status"] == "failed":
            print("**Status: FAILED**")
            if plan["error"]:
                print(f"```\n{plan['error']}\n```")
            print()
            continue

        if plan["status"] == "no_changes":
            print("**Status: NO CHANGES**")
            print()
            continue

        # Resource counts
        total = plan["adds"] + plan["changes"] + plan["destroys"]
        status_label = "CLEAN" if plan["destroys"] == 0 else "CONCERNS"
        print(f"**Status: {status_label}**")
        print(f"**Resources:** {plan['adds']} to add, {plan['changes']} to change, {plan['destroys']} to destroy")
        print()

        # Created resources
        if plan["created_resources"]:
            print("**Creating:**")
            for r in plan["created_resources"]:
                details = plan["resource_details"].get(r, [])
                if details:
                    print(f"  + {r} ({', '.join(details)})")
                else:
                    print(f"  + {r}")
            print()

        # Changed resources
        if plan["changed_resources"]:
            print("**Changing:**")
            for r in plan["changed_resources"]:
                details = plan["resource_details"].get(r, [])
                if details:
                    for d in details:
                        print(f"  ~ {r}: {d}")
                else:
                    print(f"  ~ {r}")
            print()

        # Destroyed resources
        if plan["destroyed_resources"]:
            print("**DESTROYING:**")
            for r in plan["destroyed_resources"]:
                print(f"  - {r}")
            print()

        # Warnings (deduplicated, summarized)
        unique_warnings = []
        seen = set()
        for w in plan["warnings"]:
            key = w.split(":")[0] if ":" in w else w
            if key not in seen:
                seen.add(key)
                unique_warnings.append(w)
        if unique_warnings:
            print(f"**Warnings:** ({len(plan['warnings'])} total, {len(unique_warnings)} unique)")
            for w in unique_warnings[:5]:
                print(f"  - {w}")
            if len(unique_warnings) > 5:
                print(f"  - ... and {len(unique_warnings) - 5} more")
            print()

        # Verdict
        if plan["destroys"] > 0:
            print(f"**Verdict:** {plan['destroys']} resource(s) will be destroyed — review carefully before applying.")
        else:
            apply_cmd = f"atlantis apply -p {plan['project']}" if plan["project"] else "atlantis apply"
            print(f"**Verdict:** Plan looks clean. Ready for `{apply_cmd}`.")
        print()


def list_open_prs(repo: str):
    """List open PRs and let user pick one."""
    out = run_gh([
        "pr", "list", "--repo", repo,
        "--limit", "15",
        "--json", "number,title,headRefName",
    ])
    prs = json.loads(out)
    if not prs:
        print("No open PRs found.")
        sys.exit(0)

    print("Open PRs:")
    for pr in prs:
        print(f"  #{pr['number']:>5}  {pr['title'][:70]}")
    print()
    try:
        choice = input("Enter PR number to review: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    num = extract_pr_number(choice)
    if not num:
        print("Invalid PR number.")
        sys.exit(1)
    return num


def main():
    parser = argparse.ArgumentParser(
        description="Review Atlantis plan output from a GitHub PR",
    )
    parser.add_argument(
        "pr", nargs="?", default=None,
        help="PR number or GitHub URL (omit to list open PRs)",
    )
    parser.add_argument(
        "--repo", default="grindrllc/infra-terraform",
        help="GitHub repo (default: grindrllc/infra-terraform)",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output raw parsed data as JSON",
    )
    args = parser.parse_args()

    # Get PR number
    if args.pr:
        pr_number = extract_pr_number(args.pr)
        if not pr_number:
            print(f"Could not parse PR number from: {args.pr}", file=sys.stderr)
            sys.exit(1)
    else:
        pr_number = list_open_prs(args.repo)

    # Fetch data
    pr = get_pr_details(pr_number, args.repo)
    comments = get_pr_comments(pr_number, args.repo)

    # Find and parse Atlantis plans
    atlantis_comments = find_atlantis_comments(comments)
    if not atlantis_comments:
        print(f"No Atlantis plan comments found on PR #{pr_number}.")
        sys.exit(0)

    # Use last comment (most recent plan)
    latest = atlantis_comments[-1]
    plans = [parse_plan(latest)]

    if args.json_output:
        # Strip raw field for cleaner output
        for p in plans:
            del p["raw"]
        json.dump(plans, sys.stdout, indent=2)
        print()
    else:
        print_review(pr, plans)


if __name__ == "__main__":
    main()
