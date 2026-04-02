"""Shared helpers for all .docx report generators (one-pager, valuation support, full assessment)."""
from __future__ import annotations
import datetime
from docx.shared import Pt, RGBColor
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ── Colour palette (locked — clients like the current format) ───
NAVY = RGBColor(0x1A, 0x1A, 0x2E)
BLUE = RGBColor(0x00, 0x77, 0xB6)
ORANGE_HEX = "E85D04"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY_HEX = "F5F5F5"
MUTED = RGBColor(0x66, 0x66, 0x66)

# ── Standard text blocks ───────────────────────────────────────
DISCLAIMER = (
    "This document represents Fuelled Energy Marketing Inc.\u2019s opinion of value "
    "based on available market data and proprietary methodology. It is not a certified "
    "appraisal and should not be construed as such. This report is intended solely for "
    "the use of the addressee and should not be relied upon by third parties without the "
    "express written consent of Fuelled Energy Marketing Inc. Market conditions are "
    "subject to change and values presented herein are effective as of the date noted above."
)
FOOTER_LINE = "Confidential | Fuelled Energy Marketing Inc. | valuations@fuelled.com"


# ── Formatting helpers ─────────────────────────────────────────

def price_fmt(n, currency="CAD") -> str:
    """Format a number as price string, e.g. '$150,000 CAD'. Returns '[N/A]' for None or 0."""
    if n is None or n == 0:
        return "[N/A]"
    return f"${n:,.0f} {currency}"


def ref_number(prefix="FV") -> str:
    """Generate a reference number like 'FV-2026-0401'."""
    d = datetime.date.today()
    return f"{prefix}-{d.year}-{d.month:02d}{d.day:02d}"


def today_str() -> str:
    """Return today's date formatted like 'April 01, 2026'."""
    return datetime.date.today().strftime("%B %d, %Y")


# ── Low-level docx helpers ─────────────────────────────────────

def shade(cell, hex_color: str) -> None:
    """Apply background shading to a table cell."""
    cell._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))


def navy_row(table, idx: int) -> None:
    """Apply navy background with white bold text to a table row."""
    for cell in table.rows[idx].cells:
        shade(cell, "1A1A2E")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True


def alt_shade(table, start: int = 1) -> None:
    """Apply alternating row shading (gray on even-indexed rows)."""
    for i in range(start, len(table.rows)):
        if i % 2 == 0:
            for cell in table.rows[i].cells:
                shade(cell, GRAY_HEX)


def font(run, size: int = 10, bold: bool = False, italic: bool = False, color=None) -> None:
    """Set Arial font properties on a run."""
    run.font.name = "Arial"
    run.font.size = Pt(size)
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if color:
        run.font.color.rgb = color


def border_xml(tag: str, color: str = ORANGE_HEX, sz: str = "12") -> str:
    """Generate paragraph border XML for a given side (bottom, top, etc.)."""
    return (f'<w:pBdr {nsdecls("w")}>'
            f'<w:{tag} w:val="single" w:sz="{sz}" w:space="1" w:color="{color}"/>'
            f'</w:pBdr>')


def divider(doc) -> None:
    """Add an orange bottom-border divider paragraph."""
    p = doc.add_paragraph()
    p._element.get_or_add_pPr().append(parse_xml(border_xml("bottom")))
