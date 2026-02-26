"""Facebook post fetcher."""

import os
import tempfile
from datetime import datetime

import requests

try:
    from PIL import Image
except ImportError:
    Image = None

from .models import Post
from .utils import debug_print


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
            debug_print(f"Downloaded image: {url} -> {fname} ({len(resp.content)} bytes)")
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

    def fetch_posts(self, limit=500, since=None, until=None,
                    download_images=True, search_start=90, search_end=90):
        """Fetch posts and return list of Post objects.

        Includes hidden posts (via include_hidden) and uses backdated_time
        when present so backdated posts sort to their intended date.

        Date filtering is applied client-side against the effective post date
        (backdated_time when present, otherwise created_time) so that
        backdated posts are correctly included or excluded regardless of
        when they were actually created.

        Args:
            search_start: Days before ``since`` to widen the API query.
            search_end: Days after ``until`` to widen the API query.
        """
        from datetime import timedelta

        fields = [
            "message", "created_time", "backdated_time", "is_hidden",
            "full_picture",
            "attachments{media,type,subattachments{media,type}}",
        ]
        params = {"include_hidden": "true"}

        # Widen the API query window to catch posts whose created_time
        # differs from their backdated_time, then filter client-side on
        # the effective date.
        if since:
            params["since"] = int((since - timedelta(days=search_start)).timestamp())
        if until:
            params["until"] = int((until + timedelta(days=search_end)).timestamp())

        raw_posts = self._get_paginated_posts(limit=limit, fields=fields, params=params)
        posts = []
        tmpdir = tempfile.mkdtemp(prefix="facebook_images_")

        hidden_count = sum(1 for r in raw_posts if r.get("is_hidden"))
        backdated_count = sum(1 for r in raw_posts if r.get("backdated_time"))
        if hidden_count:
            print(f"  Including {hidden_count} hidden post(s)")
        if backdated_count:
            print(f"  Found {backdated_count} backdated post(s)")

        skipped = 0
        for raw in raw_posts:
            message = raw.get("message", "")
            # Prefer backdated_time (the user-intended date) over created_time
            date_str = raw.get("backdated_time") or raw.get("created_time", "")
            try:
                post_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                post_date = post_date.replace(tzinfo=None)
            except (ValueError, AttributeError):
                post_date = datetime.now()

            # Client-side date filter on the effective (possibly backdated) date
            if since and post_date < since:
                skipped += 1
                continue
            if until and post_date > until:
                skipped += 1
                continue

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
            img_count = 0
            if download_images and Image:
                image_urls = self._extract_image_urls(raw)
                for img_url in image_urls:
                    path = self.download_image(img_url, tmpdir)
                    if path:
                        content.append(("image", path))
                        img_count += 1
            if message:
                content.append(("text", message))

            debug_print(f"Post '{title}': date={post_date}, images={img_count}")

            posts.append(Post(
                title=title,
                date=post_date,
                content=content,
            ))

        if skipped:
            debug_print(f"Skipped {skipped} post(s) outside date range "
                         f"(from widened API query)")
        posts.sort(key=lambda p: p.date)
        print(f"Fetched {len(posts)} Facebook posts total.")
        return posts
