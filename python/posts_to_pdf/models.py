"""Data models and constants for posts-to-PDF generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from reportlab.lib.pagesizes import letter, A4, legal, A3, A5, TABLOID

PAPER_SIZES = {
    "letter": letter,
    "a4": A4,
    "legal": legal,
    "a3": A3,
    "a5": A5,
    "tabloid": TABLOID,
}


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
