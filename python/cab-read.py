#!/usr/bin/env python3
"""Read/look up the Confluence CAB review page for a given date."""

import argparse
import json
import os
import re
import sys
from datetime import date

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlassian_auth import get_auth as _get_auth, add_auth_arguments


def find_cab_page(base_url, space_key, cab_date, auth):
    """Search for the CAB page by title in the given space."""
    title = f"{cab_date} Infrastructure CAB Review List"

    # First get the space ID
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

    # Search for page by title in space
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


def fetch_page_body(base_url, page_id, auth):
    """Fetch a Confluence page with storage format body."""
    resp = requests.get(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        params={"body-format": "storage"},
        auth=auth,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def extract_text(html_fragment):
    """Extract visible text from an HTML fragment, handling Confluence macros."""
    if not html_fragment:
        return ""

    # Extract Jira key from structured macro
    jira_match = re.search(r'ac:name="key">([^<]+)<', html_fragment)
    if jira_match:
        return jira_match.group(1)

    # Extract link URL
    link_match = re.search(r'href="([^"]+)"', html_fragment)
    if link_match:
        return link_match.group(1)

    # Extract user account-id (show as @user)
    user_match = re.search(r'ri:account-id="([^"]+)"', html_fragment)
    if user_match:
        return f"@{user_match.group(1)[:8]}..."

    # Strip all tags for plain text
    text = re.sub(r'<[^>]+/?>', '', html_fragment).strip()
    return text


def parse_table(body_html):
    """Parse the CAB table from the page body HTML."""
    rows_raw = re.findall(r'<tr[^>]*>(.*?)</tr>', body_html, re.DOTALL)

    headers = []
    data_rows = []

    for row_html in rows_raw:
        # Skip the title row (has colspan)
        if 'colspan' in row_html:
            continue

        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if not cells:
            continue

        texts = [extract_text(c) for c in cells]

        # Header row detection (has <strong> tags)
        if '<strong>' in row_html:
            headers = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            continue

        # Skip completely empty rows
        if all(t == "" for t in texts):
            continue

        data_rows.append(texts)

    return headers, data_rows


def format_table(headers, rows):
    """Format as an aligned text table."""
    if not headers:
        headers = ["Requester", "Jira", "GitHub", "Impact", "Rollback", "Approved", "Deployed"]

    # Truncate GitHub URLs for readability
    display_rows = []
    for row in rows:
        display = list(row)
        for i, val in enumerate(display):
            if 'github.com' in val and len(val) > 60:
                # Shorten to repo/pull/N
                m = re.search(r'github\.com/([^/]+/[^/]+/pull/\d+)', val)
                if m:
                    display[i] = m.group(1)
        display_rows.append(display)

    # Calculate column widths
    all_rows = [headers] + display_rows
    ncols = max(len(r) for r in all_rows)
    widths = [0] * ncols
    for row in all_rows:
        for i, val in enumerate(row):
            if i < ncols:
                widths[i] = max(widths[i], len(val))

    # Print
    def fmt_row(row):
        parts = []
        for i in range(ncols):
            val = row[i] if i < len(row) else ""
            parts.append(val.ljust(widths[i]))
        return " | ".join(parts)

    lines = []
    lines.append(fmt_row(headers))
    lines.append("-+-".join("-" * w for w in widths))
    for row in display_rows:
        lines.append(fmt_row(row))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Read the Confluence CAB review page")
    parser.add_argument("--date", default=str(date.today()),
                        help="Date string like 2026-03-02 (default: today)")
    parser.add_argument("--space-key", default="ISRE",
                        help="Confluence space key (default: ISRE)")
    parser.add_argument("--format", dest="output_format", default="table",
                        choices=["table", "json"],
                        help="Output format (default: table)")
    parser.add_argument("--page-id",
                        help="Direct page ID (skips search)")
    add_auth_arguments(parser)
    args = parser.parse_args()

    base_url, username, password = _get_auth(
        profile=args.profile, conf_path=args.conf,
        force_password=args.force_password,
    )
    auth = (username, password)

    if args.page_id:
        page_id = args.page_id
        page = fetch_page_body(base_url, page_id, auth)
        title = page["title"]
    else:
        page_id, title = find_cab_page(base_url, args.space_key, args.date, auth)
        page = fetch_page_body(base_url, page_id, auth)

    body = page["body"]["storage"]["value"]
    headers, rows = parse_table(body)

    print(f"# {title}")
    print(f"Page ID: {page_id} | Version: {page['version']['number']}")
    url = f"{base_url}/wiki/spaces/{args.space_key}/pages/{page_id}"
    print(f"URL: {url}")
    print()

    if not rows:
        print("No entries found.")
        return

    if args.output_format == "json":
        if not headers:
            headers = ["Requester", "Jira", "GitHub", "Impact", "Rollback", "Approved", "Deployed"]
        entries = []
        for row in rows:
            entry = {}
            for i, h in enumerate(headers):
                entry[h] = row[i] if i < len(row) else ""
            entries.append(entry)
        print(json.dumps(entries, indent=2))
    else:
        print(format_table(headers, rows))
        print(f"\n{len(rows)} entry/entries total.")


if __name__ == "__main__":
    main()
