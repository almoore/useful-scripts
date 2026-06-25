#!/usr/bin/env python3
"""Fetch a Confluence Cloud page (and optionally its children) and print it.

Usage:
    cf_get.py <url-or-id> [--format text|storage|view|adf] [--children] [--depth N]
              [--profile NAME]

Uses the shared atlassian_auth helper (config in ~/.atlassian-conf.json,
token in the OS keyring). Confluence Cloud uses v1 + v2 REST — there is no v3.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

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
        "module on PYTHONPATH. See ~/.claude/skills/confluence-read/SKILL.md."
    )

import requests


FORMAT_MAP = {
    "text": "view",         # fetched as view, then stripped to plaintext
    "storage": "storage",
    "view": "view",
    "adf": "atlas_doc_format",
}


def resolve_page_id(arg: str) -> str:
    """Accept a numeric ID, a /pages/<id>/ URL, or a ?pageId=<id> URL."""
    if arg.isdigit():
        return arg
    parsed = urlparse(arg)
    # /wiki/spaces/<KEY>/pages/<ID>/<slug>
    m = re.search(r"/pages/(\d+)(?:/|$)", parsed.path)
    if m:
        return m.group(1)
    # ?pageId=<ID>
    qs = parse_qs(parsed.query)
    if "pageId" in qs and qs["pageId"][0].isdigit():
        return qs["pageId"][0]
    sys.exit(f"Could not extract a page ID from: {arg!r}")


class _TextExtractor(HTMLParser):
    """Crude HTML → plaintext. Good enough for human review, not lossless."""

    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "br", "div", "tr"}
    CELL_TAGS = {"td", "th"}
    SKIP_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
            if tag.startswith("h"):
                self.parts.append(f"\n{'#' * int(tag[1])} ")
            elif tag == "li":
                self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        if tag in self.CELL_TAGS:
            self.parts.append(" | ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip() + "\n"


def fetch_page(base_url: str, auth, page_id: str, body_format: str) -> dict:
    r = requests.get(
        f"{base_url}/wiki/api/v2/pages/{page_id}",
        params={"body-format": body_format},
        auth=auth,
        timeout=20,
    )
    if r.status_code != 200:
        sys.exit(f"GET page {page_id} → {r.status_code}: {r.text[:400]}")
    return r.json()


def fetch_children(base_url: str, auth, page_id: str, depth: int = 1) -> list[dict]:
    """Return a flat list of children, recursing up to `depth` levels."""
    out: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(
            f"{base_url}/wiki/api/v2/pages/{page_id}/children",
            params=params,
            auth=auth,
            timeout=20,
        )
        if r.status_code != 200:
            sys.exit(f"GET children of {page_id} → {r.status_code}: {r.text[:400]}")
        data = r.json()
        for c in data.get("results", []):
            c["_depth"] = 1
            out.append(c)
            if depth > 1:
                for gc in fetch_children(base_url, auth, c["id"], depth - 1):
                    gc["_depth"] = gc.get("_depth", 1) + 1
                    out.append(gc)
        next_link = data.get("_links", {}).get("next")
        if not next_link:
            break
        m = re.search(r"cursor=([^&]+)", next_link)
        cursor = m.group(1) if m else None
        if not cursor:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("page", help="Page URL or numeric ID")
    ap.add_argument(
        "--format",
        choices=list(FORMAT_MAP.keys()),
        default="text",
        help="Output format (default: text = view HTML stripped to plaintext)",
    )
    ap.add_argument("--children", action="store_true", help="Also list child pages")
    ap.add_argument("--depth", type=int, default=1, help="Recursion depth for --children")
    ap.add_argument("--profile", default=None, help="Atlassian config profile")
    args = ap.parse_args()

    page_id = resolve_page_id(args.page)
    url, user, token = get_auth(profile=args.profile)
    auth = (user, token)

    body_format = FORMAT_MAP[args.format]
    page = fetch_page(url, auth, page_id, body_format)

    title = page.get("title", "")
    space_id = page.get("spaceId", "")
    version = page.get("version", {}).get("number", "?")
    edited = page.get("version", {}).get("createdAt", "")
    body = page.get("body", {}).get(body_format, {}).get("value", "")

    print(f"# {title}")
    print(f"id: {page_id} · spaceId: {space_id} · version: {version} · edited: {edited}")
    print(f"url: {url}/wiki/spaces/_/pages/{page_id}")
    print()

    if args.format == "text":
        print(html_to_text(body))
    else:
        print(body)

    if args.children:
        print("\n---\n## Children")
        children = fetch_children(url, auth, page_id, depth=args.depth)
        if not children:
            print("(none)")
        for c in children:
            indent = "  " * (c.get("_depth", 1) - 1)
            print(f"{indent}- id={c['id']}  {c.get('title', '')}")


if __name__ == "__main__":
    main()
