"""Save and load posts to/from files (JSON, YAML, CSV)."""

import csv
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

from .models import Post


def save_posts(posts, path):
    """Save posts to a file. Format inferred from extension (.json, .yaml/.yml, .csv)."""
    ext = os.path.splitext(path)[1].lower()

    def post_to_dict(post):
        return {
            "title": post.title,
            "date": post.date.isoformat(),
            "subtitle": post.subtitle,
            "url": post.url,
            "content": [{"type": t, "value": v} for t, v in post.content],
        }

    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump([post_to_dict(p) for p in posts], f, indent=2, ensure_ascii=False)
    elif ext in (".yaml", ".yml"):
        if yaml is None:
            print("Error: pyyaml is required for YAML output. Install with: pip install pyyaml")
            raise SystemExit(1)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump([post_to_dict(p) for p in posts], f,
                      default_flow_style=False, allow_unicode=True)
    elif ext == ".csv":
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "date", "subtitle", "url", "text"])
            for post in posts:
                text = "\n\n".join(v for t, v in post.content if t == "text")
                writer.writerow([
                    post.title,
                    post.date.isoformat(),
                    post.subtitle or "",
                    post.url or "",
                    text,
                ])
    else:
        print(f"Error: Unsupported file extension '{ext}'. Use .json, .yaml, .yml, or .csv.")
        raise SystemExit(1)

    print(f"Saved {len(posts)} posts to {path}")


def save_photos(posts, output_dir):
    """Save post images to a directory, named by post title and date."""
    os.makedirs(output_dir, exist_ok=True)
    total = 0
    for post in posts:
        image_blocks = [(t, v) for t, v in post.content if t == "image"]
        if not image_blocks:
            continue
        date_str = post.date.strftime("%Y-%m-%d")
        # Normalize Unicode (e.g. math-styled 𝐇𝐚𝐩𝐩𝐲 -> Happy) before sanitizing
        normalized = unicodedata.normalize("NFKD", post.title)
        safe_title = re.sub(r'[^a-z0-9]+', '-', normalized.lower()).strip('-')[:80]
        multi = len(image_blocks) > 1
        for i, (_, src_path) in enumerate(image_blocks, 1):
            ext = os.path.splitext(src_path)[1] or ".jpg"
            if multi:
                fname = f"{date_str}_{safe_title}_{i}{ext}"
            else:
                fname = f"{date_str}_{safe_title}{ext}"
            dest = os.path.join(output_dir, fname)
            shutil.copy2(src_path, dest)
            total += 1
    print(f"Saved {total} photo(s) to {output_dir}")


def load_posts_from_file(path):
    """Load posts from a JSON or YAML file."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif ext in (".yaml", ".yml"):
        if yaml is None:
            print("Error: pyyaml is required for YAML input. Install with: pip install pyyaml")
            raise SystemExit(1)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        print(f"Error: Unsupported file extension '{ext}' for loading. Use .json, .yaml, or .yml.")
        raise SystemExit(1)

    posts = []
    for item in data:
        content = [(block["type"], block["value"]) for block in item.get("content", [])]
        posts.append(Post(
            title=item["title"],
            date=datetime.fromisoformat(item["date"]),
            content=content,
            subtitle=item.get("subtitle"),
            url=item.get("url"),
        ))

    posts.sort(key=lambda p: p.date)
    print(f"Loaded {len(posts)} posts from {path}")
    return posts
