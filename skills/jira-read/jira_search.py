#!/usr/bin/env python3
"""Search Jira issues via JQL.

Usage:
    jira_search.py --jql "project = PROJ and status = 'In Progress'"
    jira_search.py --project PROJ --status "In Progress"
    jira_search.py --jql "..." --fields summary,status,assignee,updated
    jira_search.py --jql "..." --format json

Uses the shared atlassian_auth helper. Prefers the v3 POST /search/jql
endpoint and falls back to legacy GET /search.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

for _p in (
    os.path.join(os.environ.get("DEVOPS_SCRIPTS_DIR", ""), "lib"),
    "/Users/alexmoore/repos/github.com/almoore/useful-scripts/python",
):
    if _p and os.path.isdir(_p):
        sys.path.insert(0, _p)

try:
    from atlassian_auth import get_auth  # type: ignore
except ImportError:
    sys.exit(
        "Could not import atlassian_auth. Set DEVOPS_SCRIPTS_DIR or place the "
        "module on PYTHONPATH. See ~/.claude/skills/jira-read/SKILL.md."
    )

import requests


DEFAULT_FIELDS = ["summary", "status", "assignee", "priority", "issuetype", "updated"]


def build_jql(args) -> str:
    if args.jql:
        return args.jql
    parts: list[str] = []
    if args.project:
        parts.append(f"project = {args.project}")
    if args.status:
        parts.append(f'status = "{args.status}"')
    if args.assignee:
        parts.append(f"assignee = {args.assignee}")
    if args.label:
        for lbl in args.label:
            parts.append(f'labels = "{lbl}"')
    if not parts:
        sys.exit(
            "Must provide --jql, or at least one of "
            "--project / --status / --assignee / --label"
        )
    return " and ".join(parts) + " ORDER BY updated DESC"


def search_v3(base_url, auth, jql, fields, max_results):
    """POST /rest/api/3/search/jql with nextPageToken pagination."""
    out: list[dict] = []
    next_token: str | None = None
    while len(out) < max_results:
        payload = {
            "jql": jql,
            "fields": fields,
            "maxResults": min(100, max_results - len(out)),
        }
        if next_token:
            payload["nextPageToken"] = next_token
        r = requests.post(
            f"{base_url}/rest/api/3/search/jql",
            json=payload,
            auth=auth,
            timeout=30,
        )
        if r.status_code == 404 or r.status_code == 405:
            return None  # signal: try legacy
        if r.status_code != 200:
            sys.exit(f"Search → {r.status_code}: {r.text[:400]}")
        data = r.json()
        issues = data.get("issues", [])
        out.extend(issues)
        next_token = data.get("nextPageToken")
        if data.get("isLast", True) or not next_token or not issues:
            break
    return out[:max_results]


def search_legacy(base_url, auth, jql, fields, max_results):
    """GET /rest/api/3/search with startAt pagination."""
    out: list[dict] = []
    start_at = 0
    while len(out) < max_results:
        r = requests.get(
            f"{base_url}/rest/api/3/search",
            params={
                "jql": jql,
                "fields": ",".join(fields),
                "startAt": start_at,
                "maxResults": min(100, max_results - len(out)),
            },
            auth=auth,
            timeout=30,
        )
        if r.status_code != 200:
            sys.exit(f"Search → {r.status_code}: {r.text[:400]}")
        data = r.json()
        issues = data.get("issues", [])
        if not issues:
            break
        out.extend(issues)
        if data.get("total", 0) <= start_at + len(issues):
            break
        start_at += len(issues)
    return out[:max_results]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jql", help="Full JQL string (preferred)")
    ap.add_argument("--project", help="Shortcut: project = X")
    ap.add_argument("--status", help='Shortcut: status = "X"')
    ap.add_argument("--assignee",
                    help='Shortcut: assignee = X (use "currentUser()" for self)')
    ap.add_argument("--label", action="append",
                    help='Shortcut: labels = "X" (repeatable, AND-combined)')
    ap.add_argument("--fields", default=",".join(DEFAULT_FIELDS),
                    help="Comma-separated field IDs to return")
    ap.add_argument("--max-results", type=int, default=50,
                    help="Maximum issues to return (default: 50)")
    ap.add_argument("--format", choices=["text", "json"], default="text",
                    help="Output format (default: text)")
    ap.add_argument("--profile", default=None, help="Atlassian config profile")
    args = ap.parse_args()

    jql = build_jql(args)
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    url, user, token = get_auth(profile=args.profile)
    auth = (user, token)

    issues = search_v3(url, auth, jql, fields, args.max_results)
    if issues is None:
        issues = search_legacy(url, auth, jql, fields, args.max_results)

    if args.format == "json":
        print(json.dumps(issues, indent=2, default=str))
        return

    print(f"# {len(issues)} issue(s) — jql: {jql}")
    print()
    for i in issues:
        f = i.get("fields", {})
        key = i["key"]
        status = (f.get("status") or {}).get("name", "")
        assignee = (f.get("assignee") or {}).get("displayName", "(unassigned)")
        summary = f.get("summary", "")
        print(f"  {key:<14} [{status:<14}] {assignee:<22} {summary}")


if __name__ == "__main__":
    main()
