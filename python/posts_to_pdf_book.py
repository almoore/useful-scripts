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

Requires:
    - requests, reportlab, Pillow
    - Facebook source requires FACEBOOK_ACCESS_TOKEN env var
"""

import argparse
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO
from typing import List, Optional
from urllib.parse import urljoin

import requests

try:
    from PIL import Image
except ImportError:
    Image = None
    print("Warning: Pillow not installed. Image embedding will be disabled.")

try:
    import browser_cookie3
except ImportError:
    browser_cookie3 = None

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass
class Post:
    """Represents a single post from any source."""
    title: str
    date: datetime
    # content is a list of interleaved blocks:
    #   ("text", "paragraph text...")
    #   ("image", "/path/to/local/file.jpg")
    content: List[tuple] = field(default_factory=list)
    subtitle: Optional[str] = None
    url: Optional[str] = None


# ---------------------------------------------------------------------------
# HTML parsing helpers (stdlib html.parser, no bs4 dependency)
# ---------------------------------------------------------------------------

def _strip_substack_widgets(html):
    """Remove Substack subscription widgets and chrome from body HTML."""
    # Remove subscription widget blocks (inline CTAs, footers)
    html = re.sub(
        r'<div[^>]*class="[^"]*subscription-widget[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>',
        '', html, flags=re.DOTALL,
    )
    # Remove standalone subscribe buttons/forms
    html = re.sub(r'<form[^>]*class="[^"]*subscription[^"]*"[^>]*>.*?</form>', '', html, flags=re.DOTALL)
    # Remove "subscribe" CTA divs with class containing "preamble" or "paywall"
    html = re.sub(
        r'<div[^>]*class="[^"]*(?:preamble|paywall|subscribe-widget)[^"]*"[^>]*>.*?</div>',
        '', html, flags=re.DOTALL,
    )
    # Remove button-wrapper divs that contain subscribe links
    html = re.sub(
        r'<div[^>]*class="[^"]*button-wrapper[^"]*"[^>]*>.*?</div>',
        '', html, flags=re.DOTALL,
    )
    return html


class SubstackHTMLParser(HTMLParser):
    """Extract interleaved text and image blocks from Substack post HTML."""

    def __init__(self):
        super().__init__()
        self._text_buf = []       # accumulates text for current text block
        self.blocks = []          # list of ("text", str) | ("image", url)
        self._skip = False
        self._skip_tags = {"script", "style", "noscript", "form"}
        self._in_tag_stack = []

    def _flush_text(self):
        """Flush accumulated text buffer as a text block."""
        text = "".join(self._text_buf).strip()
        if text:
            self.blocks.append(("text", text))
        self._text_buf = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in self._skip_tags:
            self._skip = True
            self._in_tag_stack.append(tag)
            return
        # Skip divs that are subscription widgets or paywall blocks
        if tag == "div":
            cls = attrs_dict.get("class", "")
            if any(kw in cls for kw in ("subscription-widget", "paywall", "preamble")):
                self._skip = True
                self._in_tag_stack.append(tag)
                return
        if tag == "img":
            src = attrs_dict.get("src", "")
            if src and not src.startswith("data:"):
                # Flush any text before this image, then insert image block
                self._flush_text()
                self.blocks.append(("image", src))
        if tag == "br":
            self._text_buf.append("\n")
        if tag == "p":
            self._text_buf.append("\n\n")
        if tag in ("h1", "h2", "h3", "h4"):
            self._text_buf.append("\n\n")

    def handle_endtag(self, tag):
        if self._in_tag_stack and self._in_tag_stack[-1] == tag:
            self._in_tag_stack.pop()
            if not self._in_tag_stack:
                self._skip = False
            return
        if tag in ("p", "div", "li", "h1", "h2", "h3", "h4"):
            self._text_buf.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._text_buf.append(data)

    def get_blocks(self):
        """Return interleaved content blocks with footer artifacts stripped."""
        self._flush_text()

        # Strip footer artifacts from the last text block
        if self.blocks:
            last_idx = None
            for i in range(len(self.blocks) - 1, -1, -1):
                if self.blocks[i][0] == "text":
                    last_idx = i
                    break
            if last_idx is not None:
                text = self.blocks[last_idx][1]
                for marker in [
                    "PreviousNext",
                    "Discussion about this post",
                    "CommentsRestacks",
                    "Ready for more?",
                    "TopLatestDiscussions",
                ]:
                    # Only strip if marker is in the last 15% of the text
                    cutoff_pos = int(len(text) * 0.85)
                    idx = text.find(marker, cutoff_pos)
                    if idx != -1:
                        text = text[:idx].rstrip()
                        break
                if text:
                    self.blocks[last_idx] = ("text", text)
                else:
                    self.blocks.pop(last_idx)

        return self.blocks


def parse_html_content(html):
    """Parse HTML and return list of interleaved ("text", str) / ("image", url) blocks."""
    html = _strip_substack_widgets(html)
    parser = SubstackHTMLParser()
    parser.feed(html)
    return parser.get_blocks()


# ---------------------------------------------------------------------------
# SubstackFetcher
# ---------------------------------------------------------------------------

def _load_browser_cookies(domain, browser_name=None):
    """Load cookies for a domain from the user's browser.

    Args:
        domain: Domain to extract cookies for (e.g. ".substack.com").
        browser_name: Specific browser ("chrome", "firefox", "safari", "edge").
                      If None, tries all browsers in order.

    Returns:
        A cookie jar, or None if extraction failed.
    """
    if not browser_cookie3:
        print("Error: browser-cookie3 is not installed. "
              "Install with: pip install browser-cookie3")
        return None

    browsers = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "safari": browser_cookie3.safari,
        "edge": browser_cookie3.edge,
    }

    if browser_name:
        names = [browser_name]
    else:
        names = ["chrome", "firefox", "safari", "edge"]

    for name in names:
        loader = browsers.get(name)
        if not loader:
            continue
        try:
            cj = loader(domain_name=domain)
            cookie_count = sum(1 for c in cj if domain in (c.domain or ""))
            if cookie_count > 0:
                print(f"Loaded {cookie_count} cookies from {name} for {domain}")
                return cj
        except Exception as e:
            if browser_name:
                print(f"Warning: Could not load cookies from {name}: {e}")
            # Silently skip when auto-detecting

    if not browser_name:
        print("Warning: Could not find Substack cookies in any browser. "
              "Make sure you are logged in to Substack in your browser.")
    return None


class SubstackFetcher:
    """Fetch posts from a Substack publication."""

    def __init__(self, base_url, cookie=None, browser_cookies=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; posts-to-pdf-book/1.0)"
        })
        if cookie:
            self.session.headers.update({"Cookie": cookie})
        elif browser_cookies is not None:
            self.session.cookies = browser_cookies

    def _api_url(self, path):
        return f"{self.base_url}/api/v1{path}"

    def fetch_post_list(self, limit=50, offset=0):
        """Fetch post metadata list from the Substack API."""
        posts = []
        batch_size = min(limit, 50)
        while len(posts) < limit:
            url = self._api_url("/posts")
            params = {"offset": offset, "limit": batch_size}
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            posts.extend(batch)
            offset += len(batch)
            print(f"Fetched {len(posts)} post metadata entries...")
            if len(batch) < batch_size:
                break
        return posts[:limit]

    def fetch_post_content(self, post_meta):
        """Fetch full HTML content for a single post."""
        slug = post_meta.get("slug", "")
        canonical = post_meta.get("canonical_url", "")
        post_url = canonical or f"{self.base_url}/p/{slug}"

        # Use body_html from the list response if already present
        body_html = post_meta.get("body_html", "")
        if body_html:
            return body_html, post_url

        # Try the individual post API endpoint
        post_id = post_meta.get("id")
        if post_id:
            try:
                api_resp = self.session.get(self._api_url(f"/posts/{post_id}"))
                api_resp.raise_for_status()
                data = api_resp.json()
                body_html = data.get("body_html", "")
                if body_html:
                    return body_html, post_url
            except requests.RequestException:
                pass

        # Fallback: fetch the web page and extract content
        try:
            resp = self.session.get(post_url)
            resp.raise_for_status()
            match = re.search(
                r'<div[^>]*class="[^"]*body[^"]*"[^>]*>(.*?)</div>\s*(?:<div[^>]*class="[^"]*subscription|footer)',
                resp.text,
                re.DOTALL,
            )
            if match:
                return match.group(1), post_url
            return resp.text, post_url
        except requests.RequestException as e:
            print(f"Warning: Could not fetch post {slug}: {e}")
            return "", post_url

    def download_image(self, url, tmpdir):
        """Download an image and return local path."""
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "webp" in content_type:
                ext = ".webp"
            fname = os.path.join(tmpdir, f"img_{hash(url) & 0xFFFFFFFF:08x}{ext}")
            with open(fname, "wb") as f:
                f.write(resp.content)
            return fname
        except Exception as e:
            print(f"Warning: Could not download image {url}: {e}")
            return None

    def fetch_posts(self, limit=50, since=None, until=None, download_images=True):
        """Fetch posts and return list of Post objects."""
        post_metas = self.fetch_post_list(limit=limit)
        posts = []
        tmpdir = tempfile.mkdtemp(prefix="substack_images_")

        for i, meta in enumerate(post_metas):
            title = meta.get("title", "Untitled")
            subtitle = meta.get("subtitle")
            date_str = meta.get("post_date") or meta.get("published_at", "")
            try:
                # Substack dates are ISO format
                post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                post_date = post_date.replace(tzinfo=None)
            except (ValueError, AttributeError):
                post_date = datetime.now()

            if since and post_date < since:
                continue
            if until and post_date > until:
                continue

            print(f"Fetching post {i+1}/{len(post_metas)}: {title}")
            body_html, post_url = self.fetch_post_content(meta)
            blocks = parse_html_content(body_html)

            # Download images inline, replacing URL blocks with local paths
            content = []
            for block_type, block_value in blocks:
                if block_type == "image":
                    if download_images and Image:
                        path = self.download_image(block_value, tmpdir)
                        if path:
                            content.append(("image", path))
                else:
                    content.append((block_type, block_value))

            posts.append(Post(
                title=title,
                subtitle=subtitle,
                date=post_date,
                content=content,
                url=post_url,
            ))

        posts.sort(key=lambda p: p.date)
        print(f"Fetched {len(posts)} posts total.")
        return posts


# ---------------------------------------------------------------------------
# FacebookFetcher
# ---------------------------------------------------------------------------

class FacebookFetcher:
    """Fetch posts from Facebook Graph API."""

    API_BASE = "https://graph.facebook.com/v22.0/me/posts"

    def __init__(self, access_token=None):
        self.access_token = access_token or os.environ.get("FACEBOOK_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "Facebook access token required. Set FACEBOOK_ACCESS_TOKEN env var "
                "or pass --facebook-token."
            )

    def _get_paginated_posts(self, limit=500, fields=None, params=None):
        """Fetch all paginated posts from the Facebook Graph API.

        Follows pagination cursors through all available pages, merging
        query parameters from each ``next`` URL (mirrors the approach in
        facebook_profile_csv.py).
        """
        from urllib.parse import urlparse, parse_qs

        all_posts = []
        request_params = {
            "access_token": self.access_token,
            "limit": min(limit, 100),
        }
        if params:
            request_params.update(params)
        if fields:
            request_params["fields"] = ",".join(fields)

        url = self.API_BASE
        while url:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            request_params = {**request_params, **query_params}
            response = requests.get(url, params=request_params)
            if response.status_code == 200:
                data = response.json()
                all_posts.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")
                print(f"Fetched {len(all_posts)} Facebook posts so far...")
            else:
                print(f"Facebook API error: {response.status_code} {response.text}")
                break

        return all_posts

    def download_image(self, url, tmpdir):
        """Download an image and return local path."""
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            ext = ".jpg"
            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                ext = ".png"
            fname = os.path.join(tmpdir, f"fb_img_{hash(url) & 0xFFFFFFFF:08x}{ext}")
            with open(fname, "wb") as f:
                f.write(resp.content)
            return fname
        except Exception as e:
            print(f"Warning: Could not download image {url}: {e}")
            return None

    def _extract_image_urls(self, raw_post):
        """Extract unique image URLs from a Facebook post.

        Prefers subattachment images (multi-photo posts) over full_picture
        to avoid duplicates, since full_picture is typically a copy of
        the first attachment image.
        """
        urls = []

        for att in raw_post.get("attachments", {}).get("data", []):
            # Multi-photo posts: use subattachments
            subs = att.get("subattachments", {}).get("data", [])
            if subs:
                for sub in subs:
                    src = sub.get("media", {}).get("image", {}).get("src")
                    if src and src not in urls:
                        urls.append(src)
            else:
                # Single-photo: use attachment media
                src = att.get("media", {}).get("image", {}).get("src")
                if src and src not in urls:
                    urls.append(src)

        # Fall back to full_picture only if no attachment images found
        if not urls:
            pic_url = raw_post.get("full_picture")
            if pic_url:
                urls.append(pic_url)

        return urls

    def fetch_posts(self, limit=500, since=None, until=None, download_images=True):
        """Fetch posts and return list of Post objects.

        Includes hidden posts (via include_hidden) and uses backdated_time
        when present so backdated posts sort to their intended date.
        """
        fields = [
            "message", "created_time", "backdated_time", "is_hidden",
            "full_picture",
            "attachments{media,type,subattachments{media,type}}",
        ]
        params = {"include_hidden": "true"}
        if since:
            params["since"] = int(since.timestamp())
        if until:
            params["until"] = int(until.timestamp())

        raw_posts = self._get_paginated_posts(limit=limit, fields=fields, params=params)
        posts = []
        tmpdir = tempfile.mkdtemp(prefix="facebook_images_")

        hidden_count = sum(1 for r in raw_posts if r.get("is_hidden"))
        backdated_count = sum(1 for r in raw_posts if r.get("backdated_time"))
        if hidden_count:
            print(f"  Including {hidden_count} hidden post(s)")
        if backdated_count:
            print(f"  Found {backdated_count} backdated post(s)")

        for raw in raw_posts:
            message = raw.get("message", "")
            # Prefer backdated_time (the user-intended date) over created_time
            date_str = raw.get("backdated_time") or raw.get("created_time", "")
            try:
                post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                post_date = post_date.replace(tzinfo=None)
            except (ValueError, AttributeError):
                post_date = datetime.now()

            # Use first sentence of first line as title
            lines = message.strip().split("\n")
            first_line = lines[0].strip() if lines[0] else ""
            if not first_line:
                title = f"Post from {post_date.strftime('%Y-%m-%d')}"
            elif len(first_line) <= 100:
                title = first_line
            else:
                # Try to break at sentence end
                for sep in (". ", "! ", "? "):
                    idx = first_line.find(sep, 30)
                    if 0 < idx <= 100:
                        title = first_line[:idx + 1]
                        break
                else:
                    # Break at last word boundary before 100 chars
                    title = first_line[:100].rsplit(" ", 1)[0]
                    if len(title) < 30:
                        title = first_line[:100]
                    title += "..."

            # Build interleaved content: images at top, then text
            content = []
            if download_images and Image:
                image_urls = self._extract_image_urls(raw)
                for img_url in image_urls:
                    path = self.download_image(img_url, tmpdir)
                    if path:
                        content.append(("image", path))
            if message:
                content.append(("text", message))

            posts.append(Post(
                title=title,
                date=post_date,
                content=content,
            ))

        posts.sort(key=lambda p: p.date)
        print(f"Fetched {len(posts)} Facebook posts total.")
        return posts


# ---------------------------------------------------------------------------
# BookRenderer
# ---------------------------------------------------------------------------

class BookRenderer:
    """Render a list of Posts into a formatted PDF book using reportlab.platypus."""

    PAGE_WIDTH, PAGE_HEIGHT = letter
    MARGIN = 0.75 * inch

    def __init__(self, title="My Posts", output_path="book.pdf"):
        self.title = title
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._define_styles()

    def _define_styles(self):
        self.styles.add(ParagraphStyle(
            name="BookTitle",
            parent=self.styles["Title"],
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=20,
        ))
        self.styles.add(ParagraphStyle(
            name="BookSubtitle",
            parent=self.styles["Normal"],
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor="#666666",
            spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            name="ChapterTitle",
            parent=self.styles["Heading1"],
            fontSize=18,
            leading=22,
            spaceBefore=0,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="ChapterDate",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor="#888888",
            spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            name="BodyText2",
            parent=self.styles["Normal"],
            fontSize=11,
            leading=15,
            spaceAfter=8,
        ))
        self.styles.add(ParagraphStyle(
            name="TOCEntry",
            parent=self.styles["Normal"],
            fontSize=11,
            leading=16,
        ))
        self.styles.add(ParagraphStyle(
            name="TOCHeading",
            parent=self.styles["Heading1"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=20,
        ))

    # Regex to extract plain letter/digit from Unicode mathematical styled names
    _MATH_CHAR_RE = re.compile(
        r'^mathematical (?:sans-serif |monospace |script |fraktur )?'
        r'(?:bold |italic |bold italic )?'
        r'(?:capital |small )?'
        r'(?:digit )?(.+)$'
    )
    # Map word digit names to actual digits
    _DIGIT_NAMES = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    }
    _emoji_cache = {}  # maps emoji char(s) -> PNG path
    _emoji_tmpdir = None
    _emoji_swift_path = None

    # Swift helper that uses macOS CoreText for full-color emoji rendering,
    # including flag tag sequences and ZWJ families.
    _SWIFT_SOURCE = '''\
import AppKit
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else { exit(1) }
let emoji = args[1]
let outPath = args[2]
let size = CGFloat(64)

let attributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: size)
]
let attrStr = NSAttributedString(string: emoji, attributes: attributes)
let line = CTLineCreateWithAttributedString(attrStr)
let bounds = CTLineGetBoundsWithOptions(line, .useGlyphPathBounds)

let width = Int(ceil(bounds.width)) + 8
let height = Int(ceil(bounds.height)) + 8
guard width > 8 && height > 8 else { exit(1) }

let colorSpace = CGColorSpaceCreateDeviceRGB()
guard let context = CGContext(data: nil, width: width, height: height,
    bitsPerComponent: 8, bytesPerRow: width * 4,
    space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { exit(1) }

context.textPosition = CGPoint(x: 4 - bounds.origin.x, y: 4 - bounds.origin.y)
CTLineDraw(line, context)

guard let cgImage = context.makeImage() else { exit(1) }
let nsImage = NSImage(cgImage: cgImage, size: NSSize(width: width, height: height))
guard let tiffData = nsImage.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let pngData = bitmap.representation(using: .png, properties: [:]) else { exit(1) }

try! pngData.write(to: URL(fileURLWithPath: outPath))
'''

    @classmethod
    def _ensure_emoji_env(cls):
        """Set up temp dir and compile Swift emoji renderer on first use."""
        if cls._emoji_tmpdir is None:
            cls._emoji_tmpdir = tempfile.mkdtemp(prefix="emoji_render_")
            swift_src = os.path.join(cls._emoji_tmpdir, "render_emoji.swift")
            with open(swift_src, "w") as f:
                f.write(cls._SWIFT_SOURCE)
            cls._emoji_swift_path = swift_src

    @classmethod
    def _render_emoji_image(cls, emoji_str):
        """Render an emoji string to a PNG file using macOS CoreText."""
        if emoji_str in cls._emoji_cache:
            return cls._emoji_cache[emoji_str]
        cls._ensure_emoji_env()
        fname = os.path.join(
            cls._emoji_tmpdir,
            f"emoji_{hash(emoji_str) & 0xFFFFFFFF:08x}.png",
        )
        try:
            import subprocess
            result = subprocess.run(
                ["swift", cls._emoji_swift_path, emoji_str, fname],
                capture_output=True, timeout=15,
            )
            if result.returncode == 0 and os.path.exists(fname):
                cls._emoji_cache[emoji_str] = fname
                return fname
        except Exception:
            pass
        return None

    # Regex to split text into emoji sequences vs plain text runs.
    # Matches: flag sequences, ZWJ sequences, keycap sequences,
    # and standalone emoji/symbol characters.
    _EMOJI_SEQ_RE = re.compile(
        r'('
        # Flag sequences: base flag + tag chars + cancel tag
        r'[\U0001F3F4][\U000E0000-\U000E007F]+'
        r'|'
        # ZWJ sequences: emoji (+ optional modifier/VS) joined by ZWJ
        r'(?:[^\u0000-\u007F][\uFE0E\uFE0F]?'
        r'(?:\u200D[^\u0000-\u007F][\uFE0E\uFE0F]?)+'
        r')'
        r'|'
        # Keycap sequences: digit + VS16 + combining enclosing keycap
        r'[\d#*]\uFE0F?\u20E3'
        r'|'
        # Regional indicator pairs (country flags)
        r'[\U0001F1E0-\U0001F1FF]{2}'
        r'|'
        # Single emoji with optional variation selector
        r'[^\u0000-\u007F]\uFE0F?'
        r')'
    )

    @classmethod
    def _process_text(cls, text):
        """Convert fancy Unicode and emoji in text for reportlab Paragraph XML.

        - Emoji sequences (flags, ZWJ families, etc.) -> inline <img> tags
        - Mathematical styled letters/digits -> plain ASCII
        - Other emoji/symbols -> inline <img> tags
        Returns XML-safe string with embedded <img> tags for emoji.
        """
        result = []
        last_end = 0
        for m in cls._EMOJI_SEQ_RE.finditer(text):
            # Process any plain text before this match
            if m.start() > last_end:
                result.append(cls._process_plain(text[last_end:m.start()]))
            seq = m.group(0)
            # Check if this is actually just a normal character
            if len(seq) == 1 and ord(seq) <= 0xFFFF:
                cat = unicodedata.category(seq)
                if cat not in ('So', 'Sk', 'Cn'):
                    result.append(cls._escape_char(seq))
                    last_end = m.end()
                    continue
            # Check if it's a math character (single char, no modifiers)
            if len(seq) == 1 or (len(seq) == 2 and seq[1] in '\uFE0E\uFE0F'):
                base = seq[0]
                name = unicodedata.name(base, '').lower()
                if name.startswith('mathematical'):
                    plain = cls._math_to_ascii(name)
                    if plain:
                        result.append(plain)
                        last_end = m.end()
                        continue
            # Render the full emoji sequence as an inline image
            img_path = cls._render_emoji_image(seq)
            if img_path:
                result.append(
                    f'<img src="{img_path}" width="14" height="14" valign="-2"/>'
                )
            last_end = m.end()
        # Process any trailing plain text
        if last_end < len(text):
            result.append(cls._process_plain(text[last_end:]))
        return ''.join(result)

    @classmethod
    def _math_to_ascii(cls, name):
        """Convert a Unicode mathematical character name to plain ASCII."""
        m = cls._MATH_CHAR_RE.match(name)
        if not m:
            return None
        plain = m.group(1)
        if plain in cls._DIGIT_NAMES:
            return cls._DIGIT_NAMES[plain]
        if len(plain) == 1:
            return plain.upper() if 'capital' in name else plain
        return plain

    @staticmethod
    def _escape_char(ch):
        if ch == '&':
            return '&amp;'
        if ch == '<':
            return '&lt;'
        if ch == '>':
            return '&gt;'
        return ch

    @classmethod
    def _process_plain(cls, text):
        """Process a run of plain (non-emoji-sequence) text."""
        result = []
        for ch in text:
            cp = ord(ch)
            cat = unicodedata.category(ch)
            if cp <= 0xFFFF and cat not in ('So', 'Sk', 'Cn'):
                result.append(cls._escape_char(ch))
                continue
            name = unicodedata.name(ch, '').lower()
            if not name:
                continue
            if name.startswith('mathematical'):
                plain = cls._math_to_ascii(name)
                if plain:
                    result.append(plain)
                continue
            # Stray emoji/symbol outside a sequence
            img_path = cls._render_emoji_image(ch)
            if img_path:
                result.append(
                    f'<img src="{img_path}" width="14" height="14" valign="-2"/>'
                )
        return ''.join(result)

    def _escape_xml(self, text):
        """Escape text for use in reportlab Paragraph XML."""
        return self._process_text(text)

    def _build_title_page(self, posts):
        """Build title page elements."""
        elements = []
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph(self._escape_xml(self.title), self.styles["BookTitle"]))
        elements.append(Spacer(1, 0.3 * inch))

        if posts:
            date_range = f"{posts[0].date.strftime('%B %Y')} \u2013 {posts[-1].date.strftime('%B %Y')}"
            elements.append(Paragraph(date_range, self.styles["BookSubtitle"]))
            elements.append(Spacer(1, 0.2 * inch))
            count_text = f"{len(posts)} posts"
            elements.append(Paragraph(count_text, self.styles["BookSubtitle"]))

        generated = f"Generated {datetime.now().strftime('%Y-%m-%d')}"
        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(generated, self.styles["BookSubtitle"]))
        elements.append(PageBreak())
        return elements

    def _make_image_flowable(self, image_path, max_width=None, max_height=None):
        """Create a reportlab Image flowable with proper aspect ratio."""
        if not Image:
            return None
        if max_width is None:
            max_width = self.PAGE_WIDTH - 2 * self.MARGIN
        if max_height is None:
            max_height = 4 * inch

        try:
            with Image.open(image_path) as img:
                orig_w, orig_h = img.size

            aspect = orig_w / orig_h
            width = min(max_width, orig_w)
            height = width / aspect
            if height > max_height:
                height = max_height
                width = height * aspect

            return RLImage(image_path, width=width, height=height)
        except Exception as e:
            print(f"Warning: Could not process image {image_path}: {e}")
            return None

    def _build_post_elements(self, post, index):
        """Build flowable elements for a single post chapter."""
        elements = []
        title_text = self._escape_xml(post.title)
        anchor = f'<a name="post_{index}"/>'
        elements.append(Paragraph(f'{anchor}{title_text}', self.styles["ChapterTitle"]))

        date_str = post.date.strftime("%B %d, %Y")
        if post.subtitle:
            date_str += f" &mdash; {self._escape_xml(post.subtitle)}"
        elements.append(Paragraph(date_str, self.styles["ChapterDate"]))

        # Render interleaved content blocks in order
        for block_type, block_value in post.content:
            if block_type == "text":
                paragraphs = re.split(r'\n\n+', block_value.strip())
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        para_text = self._escape_xml(para).replace("\n", "<br/>")
                        elements.append(Paragraph(para_text, self.styles["BodyText2"]))
            elif block_type == "image":
                img_flowable = self._make_image_flowable(block_value)
                if img_flowable:
                    elements.append(Spacer(1, 0.15 * inch))
                    elements.append(img_flowable)
                    elements.append(Spacer(1, 0.15 * inch))

        elements.append(PageBreak())
        return elements

    def _add_page_number(self, canvas, doc):
        """Page number footer callback."""
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        page_num = canvas.getPageNumber()
        text = f"- {page_num} -"
        canvas.drawCentredString(self.PAGE_WIDTH / 2, 0.5 * inch, text)
        canvas.restoreState()

    def render(self, posts):
        """Render posts into a PDF book.

        Uses a two-pass approach: first render content to determine page numbers,
        then prepend a TOC with accurate page references.
        """
        if not posts:
            print("No posts to render.")
            return

        # --- Pass 1: Render content without TOC to get page counts ---
        # Build a temporary PDF to count pages per post
        tmp_path = self.output_path + ".tmp"
        doc = SimpleDocTemplate(
            tmp_path,
            pagesize=letter,
            leftMargin=self.MARGIN,
            rightMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN,
        )

        # Track which page each post starts on
        page_tracker = _PageTracker()

        # Title page + post content
        elements = self._build_title_page(posts)
        for i, post in enumerate(posts):
            # Insert a tracker flowable before each post
            elements.append(page_tracker.make_marker(i))
            elements.extend(self._build_post_elements(post, i))

        doc.build(elements, onFirstPage=self._add_page_number,
                  onLaterPages=self._add_page_number)

        post_pages = page_tracker.page_numbers

        # --- Pass 2: Build final PDF with TOC ---
        doc2 = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            leftMargin=self.MARGIN,
            rightMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN,
        )

        final_elements = self._build_title_page(posts)

        # TOC page(s)
        final_elements.append(Paragraph("Table of Contents", self.styles["TOCHeading"]))
        # We need to offset page numbers by the TOC pages themselves.
        # Estimate TOC pages: ~40 entries per page
        toc_entry_count = len(posts)
        estimated_toc_pages = max(1, (toc_entry_count + 39) // 40)
        # Title page = 1 page, TOC = estimated_toc_pages
        page_offset = estimated_toc_pages  # extra pages from TOC insertion

        for i, post in enumerate(posts):
            raw_page = post_pages.get(i, "?")
            if isinstance(raw_page, int):
                display_page = raw_page + page_offset
            else:
                display_page = raw_page
            title_escaped = self._escape_xml(post.title)
            date_short = post.date.strftime("%Y-%m-%d")
            toc_line = (
                f'<a href="#post_{i}" color="blue">{title_escaped}</a>'
                f' <font color="#888888">({date_short})</font>'
            )
            # Right-aligned page number using a table
            toc_data = [[
                Paragraph(toc_line, self.styles["TOCEntry"]),
                Paragraph(str(display_page), self.styles["TOCEntry"]),
            ]]
            toc_table = Table(toc_data, colWidths=[
                self.PAGE_WIDTH - 2 * self.MARGIN - 0.6 * inch,
                0.6 * inch,
            ])
            toc_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]))
            final_elements.append(toc_table)

        final_elements.append(PageBreak())

        # Post content
        for i, post in enumerate(posts):
            final_elements.extend(self._build_post_elements(post, i))

        doc2.build(final_elements, onFirstPage=self._add_page_number,
                   onLaterPages=self._add_page_number)

        # Clean up temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        print(f"PDF saved to {self.output_path}")


class _PageTracker:
    """Tracks which page each post starts on during PDF generation."""

    def __init__(self):
        self.page_numbers = {}

    def make_marker(self, post_index):
        return _PageMarkerFlowable(self, post_index)


class _PageMarkerFlowable(Flowable):
    """Zero-height flowable that records its page number during layout."""

    def __init__(self, tracker, post_index):
        super().__init__()
        self.tracker = tracker
        self.post_index = post_index
        self.width = 0
        self.height = 0

    def wrap(self, available_width, available_height):
        return (0, 0)

    def draw(self):
        self.tracker.page_numbers[self.post_index] = self.canv.getPageNumber()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pull posts from Substack or Facebook and generate a PDF book.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source", required=True, choices=["substack", "facebook"],
        help="Which platform to pull posts from.",
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
        "--limit", type=int, default=50,
        help="Maximum number of posts to fetch (default: 50).",
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip image embedding for faster generation.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    since = None
    until = None
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d")
    if args.until:
        until = datetime.strptime(args.until, "%Y-%m-%d")

    download_images = not args.no_images

    if args.source == "substack":
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
    elif args.source == "facebook":
        token = args.facebook_token or os.environ.get("FACEBOOK_ACCESS_TOKEN")
        fetcher = FacebookFetcher(access_token=token)
        default_title = "Facebook Memories"

    title = args.title or default_title

    print(f"Fetching posts from {args.source}...")
    posts = fetcher.fetch_posts(
        limit=args.limit,
        since=since,
        until=until,
        download_images=download_images,
    )

    if not posts:
        print("No posts found matching the criteria.")
        raise SystemExit(0)

    print(f"Rendering {len(posts)} posts to PDF...")
    renderer = BookRenderer(title=title, output_path=args.output)
    renderer.render(posts)


if __name__ == "__main__":
    main()
