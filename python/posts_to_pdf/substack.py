"""Substack post fetcher."""

import os
import re
import tempfile
from datetime import datetime

import requests

try:
    from PIL import Image
except ImportError:
    Image = None

from .models import Post
from .utils import debug_print
from .html_parser import parse_html_content


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
            debug_print(f"Downloaded image: {url} -> {fname} ({len(resp.content)} bytes)")
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
            img_count = 0
            for block_type, block_value in blocks:
                if block_type == "image":
                    if download_images and Image:
                        path = self.download_image(block_value, tmpdir)
                        if path:
                            content.append(("image", path))
                            img_count += 1
                else:
                    content.append((block_type, block_value))

            debug_print(f"Post '{title}': date={post_date}, images={img_count}")

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
