"""Posts-to-PDF Book Generator library.

Provides fetchers, renderers, and utilities for converting posts from
Substack or Facebook into formatted PDF books.
"""

from .models import Post, PAPER_SIZES
from .utils import debug_print, set_debug
from .html_parser import parse_html_content, SubstackHTMLParser
from .substack import SubstackFetcher
from .facebook import FacebookFetcher
from .renderer import BookRenderer
from .storage import save_posts, save_photos, load_posts_from_file

__all__ = [
    "Post",
    "PAPER_SIZES",
    "debug_print",
    "set_debug",
    "parse_html_content",
    "SubstackHTMLParser",
    "SubstackFetcher",
    "FacebookFetcher",
    "BookRenderer",
    "save_posts",
    "save_photos",
    "load_posts_from_file",
]
