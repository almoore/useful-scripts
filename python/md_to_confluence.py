#!/usr/bin/env python3
"""Convert a Markdown file to a Confluence page.

Parses Markdown into Confluence storage format (XHTML) and creates or updates
a page via the Confluence REST API. Uses atlassian_auth for authentication.

Usage:
    # Create a new page under the space homepage
    python md_to_confluence.py input.md --space ERD

    # Create under a specific parent page
    python md_to_confluence.py input.md --space ERD --parent-id 1955692790

    # Custom title (default: H1 from the file, or the filename)
    python md_to_confluence.py input.md --space ERD --title "My Page Title"

    # Update an existing page
    python md_to_confluence.py input.md --page-id 3284992029

    # Dry-run: print the converted XHTML without publishing
    python md_to_confluence.py input.md --dry-run

Requires: requests

Design notes
------------
- Targets the Confluence Cloud v1 REST API (/wiki/rest/api/content) rather
  than v2 (/wiki/api/v2/pages). v1 is simpler here because it accepts
  space:{key:...} and ancestors:[{id:...}] directly; v2 requires looking up
  the numeric spaceId first. Both work against Cloud; there is no v3.
- Storage XHTML (the editor's native format) is generated directly. ADF
  (atlas_doc_format) is not used.
- _escape_xml runs before _inline, so raw HTML in the source markdown is
  escaped rather than passed through.

Known limitations
-----------------
- No nested-list support: an indented bullet ends the outer list instead
  of starting a sub-list.
- No image support: `![alt](url)` partially matches the inline link regex
  and renders with a stray "!".
- No task-list support: `- [ ] todo` renders as a literal bullet with
  "[ ]" text.
- No Confluence-specific macros (status, info/note/warning, expand, ToC,
  intra-Confluence page links, Jira smart links). For those, hand-edit
  the --dry-run XHTML before publishing.
- Italic regex `*x*` will match across arithmetic text like `5 * 3 = 15`.
- Update path always sends a title computed from the file. If the file's
  H1 differs from the target page's current title, the page gets renamed
  — which breaks inbound <ri:page ri:content-title=...> links elsewhere
  in Confluence. Always pass --title explicitly on updates.
- No version.message on update: page history shows "(no message)".
- No 409 Conflict handling on update: a concurrent edit raises, no retry.
- Tables: <td> contents are not wrapped in <p>, and <table> lacks the
  data-layout="default" attribute the editor normally adds. Renders fine
  but breaks some later editor operations on the table.
"""

import argparse
import os
import re
import sys

import requests

# NOTE: pins atlassian_auth import to this script's directory. Move the
# script (or invoke it through a symlink resolved elsewhere) and the import
# breaks. Consider falling back to DEVOPS_SCRIPTS_DIR/lib if relocation is
# ever needed.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atlassian_auth import get_auth as _get_auth, add_auth_arguments


# ---------------------------------------------------------------------------
# Markdown -> Confluence storage format conversion
# ---------------------------------------------------------------------------

def _escape_xml(text):
    """Escape XML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text):
    """Convert inline markdown to Confluence XHTML.

    Runs AFTER _escape_xml, so any "<" / ">" in the source is already
    `&lt;` / `&gt;`. Link `&` inside URLs are also `&amp;` here, which is
    actually correct XHTML for href attribute values.
    """
    # Bold — must run before italic so ** doesn't get eaten by *
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic — KNOWN: greedy across arithmetic, e.g. "5 * 3 = 15" becomes
    # "5 <em>3 = 15</em>". Tighten with word-boundary lookarounds if needed.
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Code spans
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Links — TODO: handle images. `![alt](url)` matches the `[alt](url)`
    # tail of this pattern, leaving a stray "!" before the <a>. Either
    # add an image branch (<ac:image><ri:url ri:value="..."/></ac:image>)
    # or strip the leading "!" so the link form at least renders cleanly.
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    return text


def _make_code_macro(language, code):
    """Build a Confluence code macro block."""
    lang_attr = ""
    if language:
        lang_attr = (
            f'<ac:parameter ac:name="language">{_escape_xml(language)}</ac:parameter>'
        )
    return (
        f'<ac:structured-macro ac:name="code">'
        f'{lang_attr}'
        f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
        f'</ac:structured-macro>'
    )


def md_to_confluence(text):
    """Convert a Markdown string to Confluence storage format XHTML.

    Supports: headings (H1-H6), bold, italic, code spans, links, bullet lists,
    numbered lists, fenced code blocks, tables, blockquotes, and horizontal rules.

    Returns (title, body) where title is extracted from the first H1 (if any).
    """
    lines = text.split("\n")
    out = []
    title = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # Fenced code block
        m = re.match(r"^```(\w*)", stripped)
        if m:
            lang = m.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].rstrip().startswith("```"):
                code_lines.append(lines[i].rstrip())
                i += 1
            i += 1  # skip closing ```
            out.append(_make_code_macro(lang, "\n".join(code_lines)))
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", stripped) or re.match(r"^\*{3,}$", stripped):
            out.append("<hr />")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.+)", stripped)
        if m:
            level = len(m.group(1))
            heading_text = _inline(_escape_xml(m.group(2)))
            if level == 1 and title is None:
                title = m.group(2).strip()
            out.append(f"<h{level}>{heading_text}</h{level}>")
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].rstrip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1
            out.append(_convert_table(table_lines))
            continue

        # Unordered list
        # KNOWN: no nested-list support. An indented bullet ends the outer
        # list (rstrip strips the indent and the next iteration starts a
        # fresh <ul>).
        # KNOWN: no task-list support. `- [ ] todo` renders as a literal
        # bullet with the "[ ]" inside the <li>.
        if re.match(r"^[-*]\s+", stripped):
            list_items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].rstrip()):
                item_text = re.sub(r"^[-*]\s+", "", lines[i].rstrip())
                list_items.append(f"<li>{_inline(_escape_xml(item_text))}</li>")
                i += 1
            out.append("<ul>" + "".join(list_items) + "</ul>")
            continue

        # Ordered list — same nested/task-list caveats as <ul> above.
        if re.match(r"^\d+\.\s+", stripped):
            list_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].rstrip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].rstrip())
                list_items.append(f"<li>{_inline(_escape_xml(item_text))}</li>")
                i += 1
            out.append("<ol>" + "".join(list_items) + "</ol>")
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].rstrip().startswith(">"):
                quote_lines.append(
                    re.sub(r"^>\s?", "", lines[i].rstrip())
                )
                i += 1
            quote_body = "<br />".join(
                _inline(_escape_xml(q)) for q in quote_lines
            )
            out.append(f"<blockquote><p>{quote_body}</p></blockquote>")
            continue

        # Regular paragraph
        para_lines = []
        while (
            i < len(lines)
            and lines[i].rstrip()
            and not lines[i].rstrip().startswith("#")
            and not lines[i].rstrip().startswith("|")
            and not lines[i].rstrip().startswith("```")
            and not re.match(r"^[-*]\s+", lines[i].rstrip())
            and not re.match(r"^\d+\.\s+", lines[i].rstrip())
            and not lines[i].rstrip().startswith(">")
            and not re.match(r"^-{3,}$", lines[i].rstrip())
        ):
            para_lines.append(lines[i].rstrip())
            i += 1
        out.append(f"<p>{_inline(_escape_xml(' '.join(para_lines)))}</p>")

    return title, "\n".join(out)


def _convert_table(table_lines):
    """Convert markdown table lines to Confluence XHTML table.

    KNOWN: column-alignment from the separator row (`|:---:|---:|`) is
    discarded.
    KNOWN: emits <table> rather than <table data-layout="default"> and
    bare-text <td>/<th> cells rather than <td><p>cell</p></td>. Renders
    correctly but breaks some later editor operations on the table.
    """
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)

    if len(rows) < 2:
        return ""

    # Row 1 = header, Row 2 = separator (skip), rest = body
    header = rows[0]
    body = [r for i, r in enumerate(rows) if i >= 2]

    parts = ["<table>", "<thead><tr>"]
    for cell in header:
        parts.append(f"<th>{_inline(_escape_xml(cell))}</th>")
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{_inline(_escape_xml(cell))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Confluence API operations
# ---------------------------------------------------------------------------

def create_page(base_url, auth, space_key, title, body, parent_id=None):
    """Create a new Confluence page. Returns the page dict.

    Uses v1 (/wiki/rest/api/content) — see the module docstring "Design
    notes" for why.
    """
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body,
                "representation": "storage",
            }
        },
    }
    if parent_id:
        payload["ancestors"] = [{"id": str(parent_id)}]

    resp = requests.post(
        f"{base_url}/wiki/rest/api/content",
        json=payload,
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def update_page(base_url, auth, page_id, title, body):
    """Update an existing Confluence page. Returns the page dict.

    The `title` arg is sent as-is. If it differs from the page's current
    title, Confluence renames the page — which breaks any inbound
    <ri:page ri:content-title="..."/> links elsewhere in the space.
    Callers should pass the page's existing title unless a rename is
    actually intended. See the CLI section for the resolution rule.

    TODO: retry once on 409 Conflict (re-GET version, re-PUT) so a
    concurrent edit doesn't lose this update.
    TODO: accept an optional version-comment and forward it as
    version.message so the page-history entry is readable.
    """
    # Get current version
    resp = requests.get(
        f"{base_url}/wiki/rest/api/content/{page_id}",
        params={"expand": "version"},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    current = resp.json()
    version = current["version"]["number"] + 1

    payload = {
        "type": "page",
        "title": title,
        "version": {"number": version},
        "body": {
            "storage": {
                "value": body,
                "representation": "storage",
            }
        },
    }

    resp = requests.put(
        f"{base_url}/wiki/rest/api/content/{page_id}",
        json=payload,
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_space_homepage(base_url, auth, space_key):
    """Return the homepage page ID for a space."""
    resp = requests.get(
        f"{base_url}/wiki/rest/api/space/{space_key}",
        params={"expand": "homepage"},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("homepage", {}).get("id")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown to a Confluence page",
    )
    # TODO: accept "-" for stdin so callers can pipe converted content in
    # without a tempfile.
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument(
        "--space", "-s",
        help="Confluence space key (required for new pages)",
    )
    parser.add_argument(
        "--title", "-t",
        help="Page title (default: first H1 from the file, or filename)",
    )
    parser.add_argument(
        "--parent-id", "-p",
        help="Parent page ID (default: space homepage)",
    )
    parser.add_argument(
        "--page-id",
        help="Existing page ID to update (skips create)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print converted XHTML without publishing",
    )
    add_auth_arguments(parser)
    args = parser.parse_args()

    # Read and convert
    with open(args.input, encoding="utf-8") as f:
        md_text = f.read()

    extracted_title, body = md_to_confluence(md_text)

    # Resolve title.
    # NOTE: on update (args.page_id set), this still falls back to the
    # file's H1 / filename if --title is omitted. If that derived title
    # differs from the live page's current title, the page gets renamed
    # silently, which breaks inbound <ri:page ri:content-title="..."/>
    # links. Safer behavior would be: on update with no --title, GET the
    # current page and reuse its title. Pass --title explicitly until
    # that's fixed.
    title = (
        args.title
        or extracted_title
        or os.path.splitext(os.path.basename(args.input))[0]
    )

    if args.dry_run:
        print(f"Title: {title}\n")
        print(body)
        return

    # Authenticate
    base_url, username, password = _get_auth(
        profile=args.profile,
        conf_path=args.conf,
        force_password=args.force_password,
    )
    base_url = base_url.rstrip("/")
    auth = (username, password)

    if args.page_id:
        # Update existing page
        page = update_page(base_url, auth, args.page_id, title, body)
        page_url = f"{base_url}/wiki{page['_links']['webui']}"
        print(f"Page updated: {page_url}")
    else:
        # Create new page
        if not args.space:
            parser.error("--space is required when creating a new page")

        parent_id = args.parent_id
        if not parent_id:
            parent_id = get_space_homepage(base_url, auth, args.space)

        page = create_page(base_url, auth, args.space, title, body, parent_id)
        page_url = f"{base_url}/wiki{page['_links']['webui']}"
        print(f"Page created: {page_url}")


if __name__ == "__main__":
    main()
