#!/usr/bin/env python3
"""Add rows to a weekly Confluence CAB (Change Advisory Board) review page."""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import date

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlassian_auth import get_auth as _get_auth, get_jira_server_id, add_auth_arguments


def find_cab_page(base_url, space_key, cab_date, auth):
    """Search for the CAB page by title in the given space."""
    title = f"{cab_date} Infrastructure CAB Review List"

    resp = requests.get(
        f"{base_url}/wiki/api/v2/spaces",
        params={"keys": space_key, "limit": 1},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    spaces = resp.json().get("results", [])
    if not spaces:
        print(f"Error: Space '{space_key}' not found.", file=sys.stderr)
        sys.exit(1)
    space_id = spaces[0]["id"]

    resp = requests.get(
        f"{base_url}/wiki/api/v2/spaces/{space_id}/pages",
        params={"title": title, "limit": 5},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    pages = resp.json().get("results", [])
    if not pages:
        print(f"Error: No CAB page found for '{title}' in space {space_key}.", file=sys.stderr)
        sys.exit(1)

    return pages[0]["id"], pages[0]["title"]


def extract_page_id(page_url):
    """Extract page ID from a Confluence URL."""
    # Format: .../wiki/spaces/SPACE/pages/PAGE_ID/title
    m = re.search(r'/pages/(\d+)', page_url)
    if m:
        return m.group(1)
    # Try query param format
    m = re.search(r'pageId=(\d+)', page_url)
    if m:
        return m.group(1)
    print(f"Error: Could not extract page ID from URL: {page_url}", file=sys.stderr)
    sys.exit(1)


def get_my_account_id(base_url, auth):
    """Get the current user's Atlassian account ID."""
    resp = requests.get(f"{base_url}/rest/api/3/myself", auth=auth, timeout=15)
    resp.raise_for_status()
    return resp.json()["accountId"]


def fetch_page(base_url, page_id, auth):
    """Fetch a Confluence page with storage format body."""
    resp = requests.get(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def update_page(base_url, page_id, title, body, version, message, auth):
    """Update a Confluence page."""
    payload = {
        "id": str(page_id),
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": body,
        },
        "version": {
            "number": version,
            "message": message,
        },
    }
    resp = requests.put(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        json=payload,
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def is_empty_row(tr_html):
    """Check if a table row has all empty cells (self-closing <p/> tags only)."""
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_html, re.DOTALL)
    if not tds:
        return False
    for td in tds:
        # Strip whitespace and check if only contains empty <p .../> tags
        content = td.strip()
        cleaned = re.sub(r'<p[^/>]*/>', '', content).strip()
        if cleaned:
            return False
    return True


def build_row_html(account_id, jira_key, pr_url, impact, rollback, jira_server_id):
    """Build a filled table row in Confluence storage format."""
    rid = lambda: uuid.uuid4().hex[:12]

    user_cell = (
        f'<ac:link><ri:user ri:account-id="{account_id}" '
        f'ri:local-id="{uuid.uuid4()}" /></ac:link> '
    )

    jira_cell = (
        f'<ac:structured-macro ac:name="jira" ac:schema-version="1" '
        f'ac:local-id="{rid()}" ac:macro-id="{uuid.uuid4()}">'
        f'<ac:parameter ac:name="key">{jira_key}</ac:parameter>'
        f'<ac:parameter ac:name="serverId">{jira_server_id}</ac:parameter>'
        f'<ac:parameter ac:name="server">System Jira</ac:parameter>'
        f'</ac:structured-macro> '
    )

    pr_cell = (
        f'<a href="{pr_url}" local-id="{rid()}" '
        f'data-card-appearance="inline">{pr_url}</a> '
    )

    return (
        f'<tr ac:local-id="{rid()}">'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">{user_cell}</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">{jira_cell}</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">{pr_cell}</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">{impact}</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">{rollback}</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}">yes pending plan + approval</p></td>'
        f'<td ac:local-id="{rid()}"><p local-id="{rid()}" /></td>'
        f'</tr>'
    )


def build_empty_row():
    """Build an empty table row."""
    rid = lambda: uuid.uuid4().hex[:12]
    return (
        f'<tr ac:local-id="{rid()}">'
        + ''.join(f'<td ac:local-id="{rid()}"><p local-id="{rid()}" /></td>' for _ in range(7))
        + '</tr>'
    )


def main():
    parser = argparse.ArgumentParser(description="Add rows to a Confluence CAB review page")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--page-url", help="Confluence page URL")
    group.add_argument("--page-id", help="Confluence page ID")
    group.add_argument("--date", default=str(date.today()),
                       help="CAB date to look up (default: today, e.g. 2026-03-02)")
    parser.add_argument("--space-key", default="ISRE",
                        help="Confluence space key (default: ISRE)")
    parser.add_argument("--jira-key", action="append", required=True,
                        help="Jira ticket key (repeatable)")
    parser.add_argument("--pr-url", action="append", required=True,
                        help="GitHub PR URL (repeatable, matched 1:1 with --jira-key)")
    parser.add_argument("--impact", default="low", choices=["low", "med", "high"],
                        help="Impact level (default: low)")
    parser.add_argument("--rollback", default="revert",
                        help="Rollback plan text (default: revert)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying the page")
    add_auth_arguments(parser)
    args = parser.parse_args()

    if len(args.jira_key) != len(args.pr_url):
        print("Error: Number of --jira-key and --pr-url arguments must match.", file=sys.stderr)
        sys.exit(1)

    base_url, username, password = _get_auth(
        profile=args.profile, conf_path=args.conf,
        force_password=args.force_password,
    )
    auth = (username, password)

    # Resolve page ID
    if args.page_id:
        page_id = args.page_id
    elif args.page_url:
        page_id = extract_page_id(args.page_url)
    else:
        page_id, _ = find_cab_page(base_url, args.space_key, args.date, auth)

    # Get current user account ID
    account_id = get_my_account_id(base_url, auth)

    # Fetch current page
    page = fetch_page(base_url, page_id, auth)
    title = page["title"]
    version = page["version"]["number"]
    body = page["body"]["storage"]["value"]

    # Get Jira server ID (try from page body first, then discover)
    jira_server_id = get_jira_server_id(
        base_url, auth, profile=args.profile, conf_path=args.conf,
        page_body=body,
    )

    # Find all table rows
    rows = list(re.finditer(r'<tr[^>]*>.*?</tr>', body, re.DOTALL))

    # Find empty rows
    empty_indices = [i for i, m in enumerate(rows) if is_empty_row(m.group())]
    needed = len(args.jira_key)

    if len(empty_indices) < needed:
        # Need to add more empty rows to the table, then fill them
        extra_needed = needed - len(empty_indices)
        # Insert empty rows before the closing </tbody>
        insert_pos = body.rfind('</tbody>')
        if insert_pos == -1:
            print("Error: Could not find </tbody> in page body.", file=sys.stderr)
            sys.exit(1)
        new_empties = ''.join(build_empty_row() for _ in range(extra_needed))
        body = body[:insert_pos] + new_empties + body[insert_pos:]
        # Re-parse rows
        rows = list(re.finditer(r'<tr[^>]*>.*?</tr>', body, re.DOTALL))
        empty_indices = [i for i, m in enumerate(rows) if is_empty_row(m.group())]

    # Fill empty rows (use the first N empty ones)
    replacements = []
    for idx, (jira_key, pr_url) in enumerate(zip(args.jira_key, args.pr_url)):
        row_idx = empty_indices[idx]
        old_row = rows[row_idx].group()
        new_row = build_row_html(account_id, jira_key, pr_url, args.impact, args.rollback, jira_server_id)
        replacements.append((old_row, new_row, jira_key))

    new_body = body
    for old_row, new_row, _ in replacements:
        new_body = new_body.replace(old_row, new_row, 1)

    # Ensure there are still empty rows remaining for future entries
    remaining_empties = sum(1 for m in re.finditer(r'<tr[^>]*>.*?</tr>', new_body, re.DOTALL) if is_empty_row(m.group()))
    if remaining_empties < 3:
        insert_pos = new_body.rfind('</tbody>')
        extras = ''.join(build_empty_row() for _ in range(3 - remaining_empties))
        new_body = new_body[:insert_pos] + extras + new_body[insert_pos:]

    jira_keys_str = ", ".join(args.jira_key)

    if args.dry_run:
        print(f"DRY RUN — would update page '{title}' (id={page_id}, version {version} -> {version + 1})")
        print(f"Adding {needed} row(s): {jira_keys_str}")
        for _, _, jk in replacements:
            print(f"  - {jk}")
        return

    result = update_page(
        base_url, page_id, title, new_body, version + 1,
        f"Added {jira_keys_str} via cab-add.py",
        auth,
    )
    new_ver = result.get("version", {}).get("number", "?")
    print(f"Updated '{title}' to version {new_ver}")
    print(f"Added {needed} row(s): {jira_keys_str}")


if __name__ == "__main__":
    main()
