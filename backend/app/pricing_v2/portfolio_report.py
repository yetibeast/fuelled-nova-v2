"""Portfolio report: multi-item .docx for batch valuations."""
from __future__ import annotations
import datetime
from io import BytesIO
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

NAVY = RGBColor(0x1A, 0x1A, 0x2E)
BLUE = RGBColor(0x00, 0x77, 0xB6)
ORANGE_HEX = "E85D04"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY_HEX = "F5F5F5"
MUTED = RGBColor(0x66, 0x66, 0x66)


def _ref():
    d = datetime.date.today()
    return f"FV-PORTFOLIO-{d.year}-{d.month:02d}{d.day:02d}"


def _today():
    return datetime.date.today().strftime("%B %d, %Y")


def _price(n):
    if n is None or n == 0:
        return "[N/A]"
    return f"${n:,.0f} CAD"


def _shade(cell, hex_color):
    cell._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))


def _navy_row(table, idx):
    for cell in table.rows[idx].cells:
        _shade(cell, "1A1A2E")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True


def _alt_shade(table, start=1):
    for i in range(start, len(table.rows)):
        if i % 2 == 0:
            for cell in table.rows[i].cells:
                _shade(cell, GRAY_HEX)


def _font(run, size=10, bold=False, italic=False, color=None):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if color:
        run.font.color.rgb = color


def _border_xml(tag, color=ORANGE_HEX, sz="12"):
    return (f'<w:pBdr {nsdecls("w")}>'
            f'<w:{tag} w:val="single" w:sz="{sz}" w:space="1" w:color="{color}"/>'
            f'</w:pBdr>')


def _heading(doc, text):
    h = doc.add_heading(text, level=1)
    for r in h.runs:
        _font(r, size=14, bold=True, color=NAVY)


def _para(doc, text, **kw):
    p = doc.add_paragraph(text)
    for r in p.runs:
        _font(r, **kw)
    return p


def _table(doc, headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                _font(r, size=9, bold=True)
    _navy_row(t, 0)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    _font(r, size=9)
    _alt_shade(t)
    return t


def generate_portfolio_report(results: list[dict], batch_summary: dict) -> bytes:
    """Delegate to report_support for the upgraded portfolio report."""
    from app.pricing_v2.report_support import generate_support_report
    return generate_support_report(results, batch_summary)
