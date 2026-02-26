#!/usr/bin/env python3
"""
Posts-to-PDF Book Generator

Pull posts from Substack or Facebook and generate a formatted PDF book
with embedded images, title page, table of contents, and chapter-per-post layout.

Usage:
    # Substack (public posts)
    python posts_to_pdf_book.py --source substack \\
        --substack-url https://example.substack.com \\
        --title "My Book" --output book.pdf --limit 50

    # Substack (subscriber content with session cookie)
    python posts_to_pdf_book.py --source substack \\
        --substack-url https://example.substack.com \\
        --substack-cookie "substack.sid=..." \\
        --title "My Book" --output book.pdf

    # Facebook
    python posts_to_pdf_book.py --source facebook \\
        --title "Facebook Memories" --output fb-book.pdf \\
        --since 2020-01-01

    # Save posts to file and reload
    python posts_to_pdf_book.py --source facebook \\
        --title "Memories" --output book.pdf --save-posts posts.json

    python posts_to_pdf_book.py --source file --input-file posts.json \\
        --title "From File" --output from-file.pdf

Requires:
    - requests, reportlab, Pillow
    - Facebook source requires FACEBOOK_ACCESS_TOKEN env var
    - YAML support requires pyyaml
"""

import argparse
import os
from datetime import datetime

from posts_to_pdf import (
    PAPER_SIZES,
    BookRenderer,
    FacebookFetcher,
    SubstackFetcher,
    debug_print,
    load_posts_from_file,
    save_photos,
    save_posts,
    set_debug,
)
from posts_to_pdf.utils import _load_browser_cookies


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pull posts from Substack or Facebook and generate a PDF book.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source", required=True, choices=["substack", "facebook", "file"],
        help="Which platform to pull posts from, or 'file' to load from a saved file.",
    )
    parser.add_argument(
        "--substack-url",
        help="Substack publication URL (e.g. https://example.substack.com).",
    )
    parser.add_argument(
        "--substack-cookie",
        help="Session cookie for subscriber-only Substack content.",
    )
    parser.add_argument(
        "--browser-cookies", nargs="?", const="auto", default=None,
        metavar="BROWSER",
        help="Load Substack cookies from your browser (requires browser-cookie3). "
             "Optionally specify browser: chrome, firefox, safari, edge. "
             "Default: auto-detect.",
    )
    parser.add_argument(
        "--facebook-token",
        help="Facebook access token (overrides FACEBOOK_ACCESS_TOKEN env var).",
    )
    parser.add_argument(
        "--title", default=None,
        help="Book title (default: derived from source).",
    )
    parser.add_argument(
        "--output", default="book.pdf",
        help="Output PDF file path (default: book.pdf).",
    )
    parser.add_argument(
        "--since",
        help="Start date filter (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--until",
        help="End date filter (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--search-start", type=int, default=90,
        help="Days before --since to widen the Facebook API query, "
             "catching backdated posts (default: 90).",
    )
    parser.add_argument(
        "--search-end", type=int, default=90,
        help="Days after --until to widen the Facebook API query, "
             "catching backdated posts (default: 90).",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Maximum number of posts to fetch (default: 50).",
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip image embedding for faster generation.",
    )
    # Paper size
    parser.add_argument(
        "--paper-size", default="letter",
        choices=list(PAPER_SIZES.keys()),
        help="Paper size for the PDF (default: letter).",
    )
    # Column layout
    parser.add_argument(
        "--columns", type=int, default=1, choices=[1, 2, 3],
        help="Number of columns for post content (default: 1).",
    )
    parser.add_argument(
        "--toc-columns", type=int, default=1, choices=[1, 2, 3],
        help="Number of columns for the table of contents (default: 1).",
    )
    # Photo collation
    parser.add_argument(
        "--collate-photos", default=None, choices=["end", "per-post"],
        help="Collate photos: 'end' gathers all into a gallery, "
             "'per-post' places photos after text. Default: inline.",
    )
    # Debug
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug output.",
    )
    # Save/load
    parser.add_argument(
        "--save-posts", metavar="FILE",
        help="Save fetched posts to a file (.json, .yaml, .csv).",
    )
    parser.add_argument(
        "--input-file", metavar="PATH",
        help="Path to a saved posts file (use with --source file).",
    )
    parser.add_argument(
        "--save-photos", metavar="DIR",
        help="Save post photos to a directory, named by post title and date.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    set_debug(args.debug)

    debug_print(f"Source: {args.source}")
    debug_print(f"Paper size: {args.paper_size}, Columns: {args.columns}, "
                f"TOC columns: {args.toc_columns}")
    if args.collate_photos:
        debug_print(f"Photo collation: {args.collate_photos}")

    since = None
    until = None
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d")
    if args.until:
        until = datetime.strptime(args.until, "%Y-%m-%d")

    download_images = not args.no_images

    if args.source == "file":
        if not args.input_file:
            print("Error: --input-file is required when --source is 'file'.")
            raise SystemExit(1)
        posts = load_posts_from_file(args.input_file)
        default_title = "Posts"
    elif args.source == "substack":
        if not args.substack_url:
            print("Error: --substack-url is required for Substack source.")
            raise SystemExit(1)
        browser_cj = None
        if args.browser_cookies and not args.substack_cookie:
            domain = ".substack.com"
            browser_name = None if args.browser_cookies == "auto" else args.browser_cookies
            browser_cj = _load_browser_cookies(domain, browser_name)
        fetcher = SubstackFetcher(
            base_url=args.substack_url,
            cookie=args.substack_cookie,
            browser_cookies=browser_cj,
        )
        default_title = args.substack_url.split("//")[-1].split(".")[0].title()
        print(f"Fetching posts from {args.source}...")
        posts = fetcher.fetch_posts(
            limit=args.limit,
            since=since,
            until=until,
            download_images=download_images,
        )
    elif args.source == "facebook":
        token = args.facebook_token or os.environ.get("FACEBOOK_ACCESS_TOKEN")
        fetcher = FacebookFetcher(access_token=token)
        default_title = "Facebook Memories"
        print(f"Fetching posts from {args.source}...")
        posts = fetcher.fetch_posts(
            limit=args.limit,
            since=since,
            until=until,
            download_images=download_images,
            search_start=args.search_start,
            search_end=args.search_end,
        )

    title = args.title or default_title

    if not posts:
        print("No posts found matching the criteria.")
        raise SystemExit(0)

    # Save posts if requested
    if args.save_posts:
        save_posts(posts, args.save_posts)

    # Save photos if requested
    if args.save_photos:
        save_photos(posts, args.save_photos)

    print(f"Rendering {len(posts)} posts to PDF...")
    renderer = BookRenderer(
        title=title,
        output_path=args.output,
        paper_size=args.paper_size,
        columns=args.columns,
        toc_columns=args.toc_columns,
        collate_photos=args.collate_photos,
    )
    renderer.render(posts)


if __name__ == "__main__":
    main()
