#!/usr/bin/env python3
"""List your recently-created Jira issues.

Examples:
  jira_recent_issues.py --days 30 --max 50
  jira_recent_issues.py --days 14 --claude
  jira_recent_issues.py --project CLOUDOPS --days 60

Auth:
  Uses the same config/keyring flow as jira_auth.py (JIRA_PROFILE/JIRA_URL).
"""

import argparse
import json
from datetime import datetime

from jira_auth import setup_jira_client


def parse_args():
    p = argparse.ArgumentParser(description="List your recently-created Jira issues")
    p.add_argument("--days", type=int, default=30, help="How many days back to search")
    p.add_argument("--max", type=int, default=100, help="Maximum issues to return")
    p.add_argument("--project", help="Optional Jira project key filter (e.g., CLOUDOPS)")
    p.add_argument(
        "--claude",
        action="store_true",
        help='Filter to issues that mention "claude" (summary/description) or have label "claude"',
    )
    p.add_argument(
        "--jql",
        help="Extra JQL to AND with the generated query (e.g., statusCategory != Done)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human-readable list",
    )
    p.add_argument("--force-password", default=False, action="store_true")
    p.add_argument("-v", "--verbose", default=False, action="store_true")
    return p.parse_args()


def build_jql(args):
    parts = ["reporter = currentUser()", f"created >= -{args.days}d"]
    if args.project:
        parts.append(f"project = {args.project}")
    if args.claude:
        # `text ~` is Jira's full-text index (summary/description/comments).
        parts.append('(text ~ "claude" OR labels in ("claude"))')
    if args.jql:
        parts.append(f"({args.jql})")
    return " AND ".join(parts) + " ORDER BY created DESC"


def iter_issues(jira, jql, max_issues):
    """Iterate issues using Jira Cloud v3 search API.

    Atlassian has removed the v2 search endpoint (HTTP 410). The `jira` library
    still calls `/rest/api/2/search` in some versions, so we go directly via
    the authenticated session.
    """

    start_at = 0
    page_size = 50
    remaining = max_issues

    base = jira._options.get("server", "").rstrip("/")
    # `/rest/api/3/search` is being removed; use the enhanced endpoint.
    url = f"{base}/rest/api/3/search/jql"

    while remaining > 0:
        batch_size = min(page_size, remaining)
        payload = {
            "jql": jql,
            "maxResults": batch_size,
            "fields": ["summary", "status", "created", "labels"],
        }
        if start_at:
            # Enhanced search prefers nextPageToken, but still accepts startAt.
            payload["startAt"] = start_at

        resp = jira._session.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        issues = data.get("issues", [])
        if not issues:
            return

        for issue in issues:
            yield issue

        start_at += len(issues)
        remaining -= len(issues)
        if len(issues) < batch_size:
            return


def main():
    args = parse_args()
    jira = setup_jira_client(force_password=args.force_password, verbose=args.verbose)

    jql = build_jql(args)
    if args.verbose:
        print(f"JQL: {jql}")

    base_url = jira._options.get("server", "").rstrip("/")
    out = []
    for issue in iter_issues(jira, jql, max_issues=args.max):
        fields = issue.get("fields", {})
        created = fields.get("created")
        created_iso = None
        if created:
            # Jira returns e.g. 2026-05-28T12:34:56.789+0000
            try:
                created_iso = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%f%z").isoformat()
            except ValueError:
                created_iso = created

        out.append(
            {
                "key": issue.get("key"),
                "url": f"{base_url}/browse/{issue.get('key')}" if base_url else None,
                "created": created_iso,
                "status": (fields.get("status") or {}).get("name"),
                "summary": fields.get("summary"),
                "labels": list(fields.get("labels") or []),
            }
        )

    if args.json:
        print(json.dumps({"jql": jql, "issues": out}, indent=2))
        return 0

    if not out:
        print("No issues found.")
        return 0

    for i in out:
        created = (i.get("created") or "").split("T")[0]
        status = i.get("status") or ""
        print(f"{i['key']}  {created:<10}  {status:<15}  {i.get('summary') or ''}")
        if i.get("url"):
            print(i["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
