"""PDF book renderer using reportlab."""

import os
import re
import tempfile
import unicodedata
from collections import OrderedDict
from datetime import datetime

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import BalancedColumns

try:
    from PIL import Image
except ImportError:
    Image = None

from .models import PAPER_SIZES
from .utils import debug_print


class BookRenderer:
    """Render a list of Posts into a formatted PDF book using reportlab.platypus."""

    MARGIN = 0.75 * inch

    def __init__(self, title="My Posts", output_path="book.pdf",
                 paper_size="letter", columns=1, toc_columns=1,
                 collate_photos=None):
        self.title = title
        self.output_path = output_path
        self.columns = columns
        self.toc_columns = toc_columns
        self.collate_photos = collate_photos

        # Paper size
        size = PAPER_SIZES.get(paper_size, letter)
        self.PAGE_WIDTH, self.PAGE_HEIGHT = size

        # Column widths
        # Body columns use frame-based layout (BaseDocTemplate with multiple
        # Frame objects). TOC columns use BalancedColumns inside a single frame.
        self._gutter = 0.25 * inch
        usable = self.PAGE_WIDTH - 2 * self.MARGIN
        if columns > 1:
            self.body_col_width = (usable - self._gutter * (columns - 1)) / columns
        else:
            self.body_col_width = usable
        # TOC uses BalancedColumns (0.1*inch default spacer) inside a frame
        # that has ~12pt total padding from SimpleDocTemplate.
        bc_spacer = 0.1 * inch
        frame_padding = 12
        effective = usable - frame_padding
        if toc_columns > 1:
            self.toc_col_width = (effective - bc_spacer * (toc_columns - 1)) / toc_columns
        else:
            self.toc_col_width = usable

        self.styles = getSampleStyleSheet()
        self._define_styles()

        debug_print(f"Paper size: {paper_size} ({self.PAGE_WIDTH:.1f}x{self.PAGE_HEIGHT:.1f})")
        debug_print(f"Columns: {columns}, TOC columns: {toc_columns}")
        debug_print(f"Body col width: {self.body_col_width:.1f}, TOC col width: {self.toc_col_width:.1f}")
        if collate_photos:
            debug_print(f"Photo collation: {collate_photos}")

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
        self.styles.add(ParagraphStyle(
            name="GalleryCaption",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor="#666666",
            spaceBefore=12,
            spaceAfter=4,
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
            max_width = self.body_col_width
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
        """Build flowable elements for a single post chapter.

        Returns:
            (elements, gallery_images) tuple. gallery_images is a list of
            (image_path, post_title) tuples collected when collate_photos='end'.
        """
        elements = []
        gallery_images = []

        title_text = self._escape_xml(post.title)
        anchor = f'<a name="post_{index}"/>'
        elements.append(Paragraph(f'{anchor}{title_text}', self.styles["ChapterTitle"]))

        date_str = post.date.strftime("%B %d, %Y")
        if post.subtitle:
            date_str += f" &mdash; {self._escape_xml(post.subtitle)}"
        elements.append(Paragraph(date_str, self.styles["ChapterDate"]))

        # Collect deferred images for per-post collation
        deferred_images = []

        for block_type, block_value in post.content:
            if block_type == "text":
                paragraphs = re.split(r'\n\n+', block_value.strip())
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        para_text = self._escape_xml(para).replace("\n", "<br/>")
                        elements.append(Paragraph(para_text, self.styles["BodyText2"]))
            elif block_type == "image":
                if self.collate_photos == "end":
                    gallery_images.append((block_value, post.title))
                elif self.collate_photos == "per-post":
                    deferred_images.append(block_value)
                else:
                    # Inline (default)
                    img_flowable = self._make_image_flowable(
                        block_value, max_width=self.body_col_width)
                    if img_flowable:
                        elements.append(Spacer(1, 0.15 * inch))
                        elements.append(img_flowable)
                        elements.append(Spacer(1, 0.15 * inch))

        # per-post: append tiled photo layout after text
        if deferred_images:
            elements.extend(self._build_photo_tile(deferred_images))

        # PageBreak is added in render() loop, not here
        return elements, gallery_images

    def _build_photo_tile(self, image_paths, max_width=None):
        """Build a tiled photo layout from a list of image paths.

        - 1 image: full-width, as large as possible
        - 2+ images: 2-column grid
        """
        if max_width is None:
            max_width = self.body_col_width
        usable_height = self.PAGE_HEIGHT - 2 * self.MARGIN

        elements = []
        # Filter to valid paths only
        valid_paths = [p for p in image_paths if p]
        if not valid_paths:
            return elements

        if len(valid_paths) == 1:
            # Single image: display as large as possible
            img = self._make_image_flowable(
                valid_paths[0],
                max_width=max_width,
                max_height=usable_height - 1 * inch,
            )
            if img:
                elements.append(Spacer(1, 0.15 * inch))
                elements.append(img)
                elements.append(Spacer(1, 0.15 * inch))
        else:
            # 2+ images: 2-column grid
            gutter = 0.15 * inch
            tile_w = (max_width - gutter) / 2
            tile_h = 3 * inch

            # Build image flowables
            flowables = []
            for path in valid_paths:
                img = self._make_image_flowable(
                    path, max_width=tile_w, max_height=tile_h)
                flowables.append(img if img else "")

            # Build rows of 2
            rows = []
            for i in range(0, len(flowables), 2):
                left = flowables[i]
                right = flowables[i + 1] if i + 1 < len(flowables) else ""
                rows.append([left, right])

            table = Table(rows, colWidths=[tile_w, tile_w],
                          hAlign="CENTER")
            table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(Spacer(1, 0.15 * inch))
            elements.append(table)
            elements.append(Spacer(1, 0.15 * inch))

        return elements

    def _build_gallery_section(self, gallery_images):
        """Build a photo gallery section with all collected images.

        Groups images by post title and uses tiled layout for each group.
        """
        elements = []
        elements.append(PageBreak())
        elements.append(Paragraph("Photo Gallery", self.styles["TOCHeading"]))
        elements.append(Spacer(1, 0.3 * inch))

        # Group images by post title (preserving order)
        groups = OrderedDict()
        for img_path, post_title in gallery_images:
            groups.setdefault(post_title, []).append(img_path)

        for post_title, paths in groups.items():
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph(
                self._escape_xml(post_title),
                self.styles["GalleryCaption"]))
            elements.extend(self._build_photo_tile(paths))

        return elements

    def _add_page_number(self, canvas, doc):
        """Page number footer callback for PageTemplate.onPage."""
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        page_num = canvas.getPageNumber()
        text = f"- {page_num} -"
        canvas.drawCentredString(self.PAGE_WIDTH / 2, 0.5 * inch, text)
        canvas.restoreState()

    def _make_doc(self, path):
        """Create a document template with single and multi-column page templates.

        Uses BaseDocTemplate with multiple PageTemplates:
        - 'single': one full-width frame (title page, TOC, gallery)
        - 'body': N column frames for post content (N = self.columns)

        Content flows naturally through column frames and across pages,
        avoiding BalancedColumns limitations with long content.
        """
        pagesize = (self.PAGE_WIDTH, self.PAGE_HEIGHT)
        frame_height = self.PAGE_HEIGHT - 2 * self.MARGIN
        full_width = self.PAGE_WIDTH - 2 * self.MARGIN

        def make_frames(ncols):
            if ncols <= 1:
                return [Frame(
                    self.MARGIN, self.MARGIN,
                    full_width, frame_height,
                    id='main',
                    leftPadding=0, rightPadding=0,
                    topPadding=0, bottomPadding=0,
                )]
            col_w = (full_width - (ncols - 1) * self._gutter) / ncols
            return [
                Frame(
                    self.MARGIN + i * (col_w + self._gutter), self.MARGIN,
                    col_w, frame_height,
                    id=f'col{i}',
                    leftPadding=0, rightPadding=0,
                    topPadding=0, bottomPadding=0,
                )
                for i in range(ncols)
            ]

        templates = [
            PageTemplate(id='single', frames=make_frames(1),
                         onPage=self._add_page_number),
            PageTemplate(id='body', frames=make_frames(self.columns),
                         onPage=self._add_page_number),
        ]

        doc = BaseDocTemplate(path, pagesize=pagesize)
        doc.addPageTemplates(templates)
        return doc

    def render(self, posts):
        """Render posts into a PDF book.

        Uses a two-pass approach: first render content to determine page numbers,
        then prepend a TOC with accurate page references.

        Multi-column layout uses frame-based columns (BaseDocTemplate with
        multiple Frame objects per page) so content flows naturally across
        columns and pages without BalancedColumns size limitations.
        """
        if not posts:
            print("No posts to render.")
            return

        debug_print(f"Starting render: {len(posts)} posts")

        # --- Pass 1: Render content without TOC to get page counts ---
        tmp_path = self.output_path + ".tmp"
        doc = self._make_doc(tmp_path)

        page_tracker = _PageTracker()
        all_gallery_images = []

        # Title page (single-column); first template 'single' is used by default
        elements = self._build_title_page(posts)

        # Switch to body template for post content
        if self.columns > 1:
            elements.append(NextPageTemplate('body'))

        for i, post in enumerate(posts):
            elements.append(page_tracker.make_marker(i))
            post_elems, gallery_imgs = self._build_post_elements(post, i)
            all_gallery_images.extend(gallery_imgs)
            elements.extend(post_elems)
            elements.append(PageBreak())

        if all_gallery_images:
            if self.columns > 1:
                elements.append(NextPageTemplate('single'))
            elements.extend(self._build_gallery_section(all_gallery_images))

        debug_print("Building pass 1 (page count)...")
        doc.build(elements)

        post_pages = page_tracker.page_numbers
        debug_print(f"Pass 1 complete. Post page numbers: {post_pages}")

        # --- Pass 2: Build final PDF with TOC ---
        doc2 = self._make_doc(self.output_path)

        final_elements = self._build_title_page(posts)

        # TOC page(s) — single-column frame, BalancedColumns for multi-col TOC
        final_elements.append(Paragraph("Table of Contents", self.styles["TOCHeading"]))
        toc_entry_count = len(posts)
        estimated_toc_pages = max(1, (toc_entry_count + 39) // 40)
        page_offset = estimated_toc_pages

        debug_print(f"TOC: {toc_entry_count} entries, estimated {estimated_toc_pages} TOC pages")

        toc_entries = []
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
            # Use toc column width for multi-column TOC, full width otherwise
            toc_table_width = (self.toc_col_width if self.toc_columns > 1
                               else self.PAGE_WIDTH - 2 * self.MARGIN)
            toc_data = [[
                Paragraph(toc_line, self.styles["TOCEntry"]),
                Paragraph(str(display_page), self.styles["TOCEntry"]),
            ]]
            toc_table = Table(toc_data, colWidths=[
                toc_table_width - 0.6 * inch,
                0.6 * inch,
            ])
            toc_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]))
            toc_entries.append(toc_table)

        if self.toc_columns > 1:
            final_elements.append(BalancedColumns(toc_entries, nCols=self.toc_columns))
        else:
            final_elements.extend(toc_entries)

        final_elements.append(PageBreak())

        # Switch to body template for post content
        if self.columns > 1:
            final_elements.append(NextPageTemplate('body'))

        # Post content (pass 2)
        all_gallery_images_2 = []
        for i, post in enumerate(posts):
            post_elems, gallery_imgs = self._build_post_elements(post, i)
            all_gallery_images_2.extend(gallery_imgs)
            final_elements.extend(post_elems)
            final_elements.append(PageBreak())

        if all_gallery_images_2:
            if self.columns > 1:
                final_elements.append(NextPageTemplate('single'))
            final_elements.extend(self._build_gallery_section(all_gallery_images_2))

        debug_print("Building pass 2 (final PDF)...")
        doc2.build(final_elements)

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
