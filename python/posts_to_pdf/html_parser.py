"""HTML parsing helpers for Substack post content (stdlib html.parser, no bs4)."""

import re
from html.parser import HTMLParser


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
