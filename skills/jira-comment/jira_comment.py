#!/usr/bin/env python3
"""Add a comment to a Jira Cloud issue.

Usage:
    jira_comment.py <key-or-url> --body "text"
    jira_comment.py <key-or-url> --body-file notes.md   # "-" reads stdin
    echo "text" | jira_comment.py <key-or-url>
        [--format wiki|adf] [--visibility-group NAME | --visibility-role NAME]
        [--dry-run] [--profile NAME]

Uses the shared atlassian_auth helper (config in ~/.atlassian-conf.json,
token in the OS keyring) — the same credentials as jira-get / jira-create.

Two body formats:
  wiki (default) — POST the raw string to v2; Jira renders it as wiki markup
                   (h3., *bold*, `*` bullets, `#` numbered, {{mono}}, {code}).
                   Highest fidelity for human-readable notes.
  adf            — wrap plaintext into an ADF document and POST to v3. Use when
                   the body contains literal * or { that must NOT be parsed as
                   markup, or when you want guaranteed-plain paragraphs.
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
        "module on PYTHONPATH. See ~/.claude/skills/jira-comment/SKILL.md."
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


def read_body(args) -> str:
    """Resolve the comment body from --body, --body-file, or stdin."""
    if args.body is not None:
        body = args.body
    elif args.body_file is not None:
        if args.body_file == "-":
            body = sys.stdin.read()
        else:
            with open(args.body_file, "r", encoding="utf-8") as fh:
                body = fh.read()
    elif not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        sys.exit("No comment body. Pass --body, --body-file, or pipe text on stdin.")
    body = body.strip("\n")
    if not body.strip():
        sys.exit("Refusing to post an empty comment.")
    return body


def text_to_adf(body: str) -> dict:
    """Wrap plaintext into a minimal ADF doc: blank lines split paragraphs,
    single newlines become hardBreaks. Lossless for plain text, no markup."""
    doc: dict = {"type": "doc", "version": 1, "content": []}
    for block in re.split(r"\n\s*\n", body):
        block = block.strip("\n")
        if not block:
            continue
        nodes: list = []
        lines = block.split("\n")
        for i, line in enumerate(lines):
            if line:
                nodes.append({"type": "text", "text": line})
            if i < len(lines) - 1:
                nodes.append({"type": "hardBreak"})
        doc["content"].append({"type": "paragraph", "content": nodes})
    if not doc["content"]:
        doc["content"].append({"type": "paragraph", "content": []})
    return doc


def build_payload(args, body: str) -> tuple[str, dict]:
    """Return (api_version, json_payload) for the chosen format."""
    if args.format == "adf":
        payload: dict = {"body": text_to_adf(body)}
        api = "3"
    else:  # wiki
        payload = {"body": body}
        api = "2"

    if args.visibility_group:
        payload["visibility"] = {"type": "group", "value": args.visibility_group}
    elif args.visibility_role:
        payload["visibility"] = {"type": "role", "value": args.visibility_role}
    return api, payload


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("issue", help="Issue key (PROJ-123) or browse URL")
    body_group = ap.add_mutually_exclusive_group()
    body_group.add_argument("--body", help="Comment body as a literal string")
    body_group.add_argument("--body-file",
                            help='Path to a file with the body ("-" = stdin)')
    ap.add_argument("--format", choices=["wiki", "adf"], default="wiki",
                    help="Body format (default: wiki markup via v2)")
    vis = ap.add_mutually_exclusive_group()
    vis.add_argument("--visibility-group",
                     help="Restrict comment visibility to a group name")
    vis.add_argument("--visibility-role",
                     help="Restrict comment visibility to a project role name")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the resolved key and payload; do not post")
    ap.add_argument("--profile", default=None, help="Atlassian config profile")
    args = ap.parse_args()

    key = resolve_issue_key(args.issue)
    body = read_body(args)
    api, payload = build_payload(args, body)

    if args.dry_run:
        print(f"[dry-run] would POST to /rest/api/{api}/issue/{key}/comment")
        print(json.dumps(payload, indent=2))
        return

    url, user, token = get_auth(profile=args.profile)
    r = requests.post(
        f"{url}/rest/api/{api}/issue/{key}/comment",
        json=payload,
        auth=(user, token),
        timeout=20,
    )
    if r.status_code not in (200, 201):
        sys.exit(f"POST comment {key} → {r.status_code}: {r.text[:400]}")

    cid = r.json().get("id", "")
    base = url.rstrip("/")
    print(f"Comment added to {key} (id {cid})")
    print(f"{base}/browse/{key}?focusedCommentId={cid}")


if __name__ == "__main__":
    main()
