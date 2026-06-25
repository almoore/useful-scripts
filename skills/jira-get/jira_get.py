#!/usr/bin/env python3
"""Fetch a Jira Cloud issue and print it.

Usage:
    jira_get.py <key-or-url> [--format text|json|adf] [--comments] [--subtasks]
                [--changelog] [--profile NAME]

Uses the shared atlassian_auth helper (config in ~/.atlassian-conf.json,
token in the OS keyring). Jira Cloud uses v2 (wiki markup) and v3 (ADF) —
prefer v3 for new code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

# Make atlassian_auth importable from either canonical location
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
        "module on PYTHONPATH. See ~/.claude/skills/jira-get/SKILL.md."
    )

import requests


KEY_RE = re.compile(r"\b([A-Z][A-Z0-9_]+-\d+)\b")


def resolve_issue_key(arg: str) -> str:
    """Accept PROJ-123, a /browse/PROJ-123 URL, or selectedIssue=PROJ-123."""
    parsed = urlparse(arg)
    if parsed.scheme:
        m = re.search(r"/browse/([A-Z][A-Z0-9_]+-\d+)", parsed.path)
        if m:
            return m.group(1)
        m = re.search(r"selectedIssue=([A-Z][A-Z0-9_]+-\d+)", parsed.query)
        if m:
            return m.group(1)
    m = KEY_RE.search(arg)
    if m:
        return m.group(1)
    sys.exit(f"Could not extract an issue key from: {arg!r}")


def adf_to_text(node) -> str:
    """Crude ADF → plaintext. Good for human review, not lossless."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    t = node.get("type", "")
    parts: list[str] = []

    if t == "text":
        parts.append(node.get("text", ""))
    elif t == "hardBreak":
        parts.append("\n")
    elif t == "mention":
        parts.append("@" + node.get("attrs", {}).get("text", "mention"))
    elif t == "inlineCard":
        parts.append(node.get("attrs", {}).get("url", "[link]"))
    elif t == "emoji":
        parts.append(node.get("attrs", {}).get("shortName", ""))

    for child in node.get("content", []) or []:
        parts.append(adf_to_text(child))

    s = "".join(parts)

    if t == "heading":
        lvl = node.get("attrs", {}).get("level", 1)
        return "#" * lvl + " " + s + "\n\n"
    if t == "paragraph":
        return s + "\n\n"
    if t in ("bulletList", "orderedList"):
        return s + "\n"
    if t == "listItem":
        return "- " + s.strip() + "\n"
    if t == "codeBlock":
        return "```\n" + s + "\n```\n\n"
    if t == "rule":
        return "\n---\n\n"
    if t == "blockquote":
        return "> " + s.strip().replace("\n", "\n> ") + "\n\n"
    return s


def fetch_issue(base_url: str, auth, key: str, expand=None) -> dict:
    params = {}
    if expand:
        params["expand"] = ",".join(expand)
    r = requests.get(
        f"{base_url}/rest/api/3/issue/{key}",
        params=params,
        auth=auth,
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"GET issue {key} → {r.status_code}: {r.text[:400]}")
    return r.json()


def fmt_user(u) -> str:
    if not u:
        return "(unassigned)"
    return f"{u.get('displayName','')} <{u.get('emailAddress', u.get('accountId',''))}>"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("issue", help="Issue key (PROJ-123) or browse URL")
    ap.add_argument(
        "--format",
        choices=["text", "json", "adf"],
        default="text",
        help="Output format (default: text)",
    )
    ap.add_argument("--comments", action="store_true", help="Include comments")
    ap.add_argument("--subtasks", action="store_true", help="List subtasks")
    ap.add_argument("--changelog", action="store_true", help="Include change history")
    ap.add_argument("--profile", default=None, help="Atlassian config profile")
    args = ap.parse_args()

    key = resolve_issue_key(args.issue)
    url, user, token = get_auth(profile=args.profile)
    auth = (user, token)

    expand = ["renderedFields"]
    if args.changelog:
        expand.append("changelog")
    if args.subtasks:
        expand.append("subtasks")
    issue = fetch_issue(url, auth, key, expand=expand)
    f = issue["fields"]

    if args.format == "json":
        print(json.dumps(issue, indent=2, default=str))
        return

    print(f"# [{key}] {f.get('summary','')}")
    print(f"url: {url.rstrip('/')}/browse/{key}")
    print(
        f"type: {f.get('issuetype',{}).get('name','')} · "
        f"status: {f.get('status',{}).get('name','')} · "
        f"priority: {(f.get('priority') or {}).get('name','')}"
    )
    print(f"assignee: {fmt_user(f.get('assignee'))}")
    print(f"reporter: {fmt_user(f.get('reporter'))}")
    parent = f.get("parent")
    if parent:
        psum = parent.get("fields", {}).get("summary", "")
        print(f"parent:   {parent['key']}  {psum}")
    if f.get("labels"):
        print(f"labels:   {', '.join(f['labels'])}")
    if f.get("components"):
        print(f"components: {', '.join(c['name'] for c in f['components'])}")
    if f.get("fixVersions"):
        print(f"fixVersions: {', '.join(v['name'] for v in f['fixVersions'])}")
    print(f"created:  {f.get('created','')}")
    print(f"updated:  {f.get('updated','')}")
    print()

    desc = f.get("description")
    if args.format == "adf":
        print(json.dumps(desc, indent=2))
    else:
        if isinstance(desc, dict):
            text = adf_to_text(desc).strip()
            print(text or "(no description)")
        elif isinstance(desc, str):
            print(desc)
        else:
            print("(no description)")
    print()

    if args.subtasks:
        subtasks = f.get("subtasks") or []
        if subtasks:
            print("## Subtasks")
            for s in subtasks:
                sf = s.get("fields", {})
                st = sf.get("status", {}).get("name", "")
                print(f"- {s['key']} [{st}] {sf.get('summary','')}")
            print()

    if args.comments:
        r = requests.get(
            f"{url}/rest/api/3/issue/{key}/comment",
            params={"maxResults": 100},
            auth=auth,
            timeout=20,
        )
        if r.status_code == 200:
            comments = r.json().get("comments", [])
            if comments:
                print("## Comments")
                for c in comments:
                    author = c.get("author", {}).get("displayName", "")
                    when = c.get("created", "")
                    body = c.get("body")
                    text = adf_to_text(body).strip() if isinstance(body, dict) else (body or "")
                    print(f"### {author} — {when}")
                    print(text)
                    print()

    if args.changelog:
        cl = issue.get("changelog", {}).get("histories", [])
        if cl:
            print("## Changelog")
            for h in cl:
                who = h.get("author", {}).get("displayName", "")
                when = h.get("created", "")
                for item in h.get("items", []):
                    field = item.get("field", "")
                    fr = item.get("fromString") or ""
                    to = item.get("toString") or ""
                    print(f"- {when} · {who}: {field} {fr!r} → {to!r}")


if __name__ == "__main__":
    main()
