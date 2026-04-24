"""Tests for the LLM-fallback batch extractor parser.

These tests exercise the pure JSONL parser — no network, no API key needed.
The extractor is designed so that if the LLM's output is truncated mid-line
(max_tokens hit), earlier complete lines survive.
"""
from app.pricing_v2.batch_extractor import _parse_items


def test_parse_jsonl_happy_path():
    text = (
        '{"title":"Ariel JGK/4","category":"compressor","specs":{"hp":750}}\n'
        '{"title":"Waukesha VHP","category":"engine","specs":{}}\n'
    )
    items = _parse_items(text)
    assert len(items) == 2
    assert items[0]["title"] == "Ariel JGK/4"
    assert items[0]["specs"]["hp"] == 750
    assert items[1]["category"] == "engine"


def test_parse_jsonl_skips_truncated_final_line():
    """If Claude's output is cut mid-line, the trailing partial JSON is dropped."""
    text = (
        '{"title":"Tank 1","category":"tank","specs":{"location":"site-A"}}\n'
        '{"title":"Tank 2","category":"tank","specs":{"locatio'  # truncated
    )
    items = _parse_items(text, truncated_output=True)
    assert len(items) == 1
    assert items[0]["title"] == "Tank 1"


def test_parse_jsonl_skips_single_malformed_line_in_middle():
    text = (
        '{"title":"A","category":"tank","specs":{}}\n'
        '{not valid json}\n'
        '{"title":"C","category":"pump","specs":{}}\n'
    )
    items = _parse_items(text)
    assert [it["title"] for it in items] == ["A", "C"]


def test_parse_jsonl_strips_code_fences():
    text = '```jsonl\n{"title":"X","category":"other","specs":{}}\n```'
    items = _parse_items(text)
    assert len(items) == 1
    assert items[0]["title"] == "X"


def test_parse_jsonl_drops_items_without_title():
    text = (
        '{"title":"","category":"tank","specs":{}}\n'
        '{"category":"pump"}\n'
        '{"title":"Keeper","category":"","specs":{}}\n'
    )
    items = _parse_items(text)
    assert len(items) == 1
    assert items[0]["title"] == "Keeper"


def test_parse_json_array_fallback():
    """If the model slips into array mode anyway, we still parse it."""
    text = '[{"title":"A","category":"tank","specs":{}},{"title":"B","category":"pump","specs":{}}]'
    items = _parse_items(text)
    assert [it["title"] for it in items] == ["A", "B"]


def test_parse_items_defaults_missing_fields():
    text = '{"title":"Bare"}\n'
    items = _parse_items(text)
    assert items == [{"title": "Bare", "category": "", "specs": {}}]


def test_parse_empty_text_returns_empty_list():
    assert _parse_items("") == []
    assert _parse_items("   \n\n  ") == []
