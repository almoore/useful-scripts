#!/usr/bin/env python3
"""Render Markdown to HTML and put it on the macOS clipboard as rich text.

Chat apps like Microsoft Teams format pasted HTML but show pasted Markdown as
raw text. This does what copying from an editor's Markdown preview does: the
clipboard gets an HTML flavor (used by Teams, Outlook, Confluence, Docs) plus a
plain-text flavor with the original Markdown as a fallback.

Supports tables, fenced code blocks and nested lists.

Usage:
    md_to_clipboard.py draft.md              # copy rendered draft.md
    cat draft.md | md_to_clipboard.py        # read from stdin
    md_to_clipboard.py draft.md --html       # print the HTML instead of copying

Requires: markdown (pip install markdown); macOS (uses osascript)
"""

import argparse
import subprocess
import sys

import markdown


def render(md_text):
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    return f'<html><head><meta charset="utf-8"></head><body>{body}</body></html>'


def copy_to_clipboard(html, plain):
    # AppleScript record sets both clipboard flavors at once; HTML goes in as hex
    # so no quoting of the markup is needed.
    escaped = plain.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        f'set the clipboard to {{«class HTML»:«data HTML{html.encode("utf-8").hex()}», '
        f'string:"{escaped}"}}'
    )
    subprocess.run(["osascript", "-e", script], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", nargs="?", help="Markdown file (default: stdin)")
    parser.add_argument("--html", action="store_true", help="print the HTML instead of copying")
    args = parser.parse_args()

    if args.file and args.file != "-":
        with open(args.file, encoding="utf-8") as f:
            md_text = f.read()
    else:
        md_text = sys.stdin.read()

    html = render(md_text)
    if args.html:
        print(html)
        return

    copy_to_clipboard(html, md_text)
    print(f"Copied {len(html)} bytes of HTML to the clipboard", file=sys.stderr)


if __name__ == "__main__":
    main()
