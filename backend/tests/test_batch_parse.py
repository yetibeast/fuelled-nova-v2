"""Tests for the fast-path spreadsheet parser in app.api.batch.

Regression coverage for the 2026-05-29 "Optimum Tech" batch upload, which
reported "14/14 priced, $0/$0". Three defects:

1. ``_detect_columns`` let one column satisfy two fields ("Type of Equipment"
   matched both ``title`` via "equipment" and ``category`` via "type"), so
   category collapsed onto the title column and came out empty.
2. ``_try_schema_parse`` accepted a header that mapped ONLY ``title`` (e.g. a
   form-style sheet whose first cell is "Name"), then slurped the company name,
   a date cell, and the real header row in as "equipment" items instead of
   routing the messy layout to the LLM extractor.
3. ``_price_batch`` counted items that priced to an empty/$0 valuation as
   "completed", masking the failure.
"""
import asyncio

import openpyxl
from io import BytesIO

from app.api import batch
from app.api.batch import _detect_columns, _try_schema_parse, _price_batch, BatchItem


def _xlsx(rows: list[list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── 1. Column detection must not let one column claim two fields ──────────
def test_detect_columns_does_not_double_map_title_and_category():
    """"Type of Equipment" matches both hints; title wins, category stays unmapped."""
    col_map = _detect_columns(["Type of Equipment", "Make", "Model"])
    assert col_map.get("title") == 0
    # The same column must not also be claimed as category.
    assert col_map.get("category") != 0
    assert "category" not in col_map


def test_detect_columns_clean_header_still_maps():
    """A genuinely clean header must keep mapping every field as before."""
    col_map = _detect_columns(["Title", "Category", "Make", "Model", "Year"])
    assert col_map["title"] == 0
    assert col_map["category"] == 1
    assert col_map["make"] == 2


# ── 2. Low-confidence header routes to the LLM extractor (returns None) ────
def test_form_style_sheet_routes_to_llm_extractor():
    """A title-only header above metadata must NOT be force-parsed into items.

    This is the Optimum Tech shape: a generic label cell, then the company
    name, a date, the real sub-table header, and bare type words below it.
    """
    data = _xlsx([
        ["Name"],
        ["Optimum Tech"],
        ["2026-05-26"],
        ["Type of Equipment"],
        ["Compressor Package"],
        ["Pump"],
    ])
    # None signals _parse_file_to_items to fall through to the LLM extractor.
    assert _try_schema_parse(data, "xlsx") is None


def test_confident_header_still_uses_fast_path():
    """A header with title + a corroborating field stays on the fast path."""
    data = _xlsx([
        ["Description", "Category", "Make"],
        ["Ariel JGK4 compressor", "compressor", "Ariel"],
    ])
    items = _try_schema_parse(data, "xlsx")
    assert items is not None
    assert len(items) == 1
    assert items[0].title == "Ariel JGK4 compressor"
    assert items[0].category == "compressor"


# ── 3. Empty/$0 valuations are reported as failures, not completions ──────
def test_empty_valuation_counts_as_failed(monkeypatch):
    """An item that prices with no FMV must land in errors, not results."""
    async def fake_empty(_user_msg):
        return {"structured": {}, "response": "Insufficient detail to value.",
                "confidence": "LOW", "tools_used": []}

    monkeypatch.setattr(batch, "run_pricing", fake_empty)
    out = asyncio.run(_price_batch([BatchItem(title="Pump", category="")]))
    assert out["summary"]["completed"] == 0
    assert out["summary"]["failed"] == 1


def test_real_valuation_still_counts_as_completed(monkeypatch):
    """A normal priced item is unaffected by the empty-row guard."""
    async def fake_priced(_user_msg):
        return {"structured": {"valuation": {"fmv_low": 600, "fmv_high": 1100}},
                "response": "ok", "confidence": "MEDIUM",
                "tools_used": ["search_comparables"]}

    monkeypatch.setattr(batch, "run_pricing", fake_priced)
    out = asyncio.run(_price_batch([BatchItem(title="3in ball valve", category="Valve")]))
    assert out["summary"]["completed"] == 1
    assert out["summary"]["failed"] == 0
    assert out["summary"]["total_fmv_low"] == 600
