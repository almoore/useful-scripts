#!/usr/bin/env python3
"""Convert a Markdown file to a styled PDF using ReportLab.

Supports headings (H1-H3), bold/italic, bullet lists, tables, links,
code spans, and highlighted lines (using >>> markers).

Usage:
    python scripts/md_to_pdf.py input.md                  # outputs input.pdf
    python scripts/md_to_pdf.py input.md -o output.pdf    # custom output path

Requires: reportlab (pip install reportlab)
"""

import argparse
import os
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _make_styles():
    """Create custom paragraph styles."""
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "DocTitle", parent=base["Title"],
            fontSize=18, leading=22, spaceAfter=6,
        ),
        "H2": ParagraphStyle(
            "H2x", parent=base["Heading2"],
            fontSize=14, leading=18, spaceBefore=16, spaceAfter=8,
            textColor=HexColor("#1a365d"),
        ),
        "H3": ParagraphStyle(
            "H3x", parent=base["Heading3"],
            fontSize=12, leading=15, spaceBefore=12, spaceAfter=6,
            textColor=HexColor("#2c5282"),
        ),
        "Body": ParagraphStyle(
            "Bodyx", parent=base["Normal"],
            fontSize=10, leading=14, spaceAfter=6,
        ),
        "Highlight": ParagraphStyle(
            "Highlightx", parent=base["Normal"],
            fontSize=10, leading=14, spaceAfter=6,
            backColor=HexColor("#FFFDE7"),
            borderColor=HexColor("#F9A825"),
            borderWidth=1, borderPadding=6,
        ),
        "Bullet": ParagraphStyle(
            "BulletItemx", parent=base["Normal"],
            fontSize=10, leading=14, leftIndent=20, bulletIndent=8,
            spaceAfter=4,
        ),
        "TableCell": ParagraphStyle(
            "TableCellx", parent=base["Normal"],
            fontSize=8.5, leading=11,
        ),
        "Italic": ParagraphStyle(
            "Italicx", parent=base["Normal"],
            fontSize=9, leading=13, textColor=HexColor("#555555"),
            spaceAfter=6,
        ),
    }


def _clean(text):
    """Escape XML and convert inline markdown to ReportLab XML tags."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="9">\1</font>', text)
    text = re.sub(
        r"\[(.+?)\]\((.+?)\)", r'<a href="\2" color="#2c5282">\1</a>', text
    )
    return text


def _flush_table(table_rows, elements, styles):
    """Convert accumulated table rows into a ReportLab Table."""
    if not table_rows or len(table_rows) < 2:
        return
    # Skip separator row (row index 1 with dashes)
    data = [r for i, r in enumerate(table_rows) if i != 1]
    col_count = len(data[0])
    avail = letter[0] - 1.5 * inch
    col_widths = [avail / col_count] * col_count

    styled_data = []
    for row in data:
        styled_data.append([
            Paragraph(
                cell.replace("&gt;&gt;&gt;", "<b>").replace("&lt;&lt;&lt;", "</b>"),
                styles["TableCell"],
            )
            for cell in row
        ])

    t = Table(styled_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#2c5282")),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [HexColor("#ffffff"), HexColor("#f7fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8))


def convert(input_path, output_path=None):
    """Convert a Markdown file to PDF.

    Args:
        input_path: Path to the input .md file.
        output_path: Path for the output .pdf. Defaults to input with .pdf extension.

    Returns:
        The output path.
    """
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".pdf"

    with open(input_path, encoding="utf-8") as f:
        lines = f.readlines()

    styles = _make_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )

    elements = []
    table_rows = []
    in_table = False

    for line in lines:
        raw = line.rstrip()

        # Table rows
        if raw.startswith("|"):
            cells = [c.strip() for c in raw.split("|")[1:-1]]
            if cells:
                in_table = True
                table_rows.append([_clean(c) for c in cells])
            continue
        elif in_table:
            _flush_table(table_rows, elements, styles)
            table_rows = []
            in_table = False

        if not raw.strip():
            continue

        # Horizontal rule
        if raw.strip() == "---":
            elements.append(Spacer(1, 4))
            continue

        # Headings
        if raw.startswith("# "):
            elements.append(Paragraph(_clean(raw[2:]), styles["Title"]))
            continue
        if raw.startswith("## "):
            elements.append(Paragraph(_clean(raw[3:]), styles["H2"]))
            continue
        if raw.startswith("### "):
            elements.append(Paragraph(_clean(raw[4:]), styles["H3"]))
            continue

        # Highlighted lines (>>> markers)
        if ">>>" in raw:
            text = raw.replace(">>>", "").replace("<<<", "").strip()
            text = re.sub(r"^\*\*|\*\*$", "", text)
            elements.append(Paragraph(f"<b>{_clean(text)}</b>", styles["Highlight"]))
            continue

        # Bullet list
        if raw.startswith("- "):
            elements.append(
                Paragraph(_clean(raw[2:]), styles["Bullet"], bulletText="\u2022")
            )
            continue

        # Standalone italic
        if raw.startswith("*") and raw.endswith("*") and not raw.startswith("**"):
            elements.append(
                Paragraph(f"<i>{_clean(raw[1:-1])}</i>", styles["Italic"])
            )
            continue

        # Regular paragraph
        elements.append(Paragraph(_clean(raw), styles["Body"]))

    if in_table:
        _flush_table(table_rows, elements, styles)

    doc.build(elements)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to PDF")
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("-o", "--output", help="Output PDF path (default: <input>.pdf)")
    args = parser.parse_args()
    out = convert(args.input, args.output)
    print(f"PDF saved: {out}")


if __name__ == "__main__":
    main()
