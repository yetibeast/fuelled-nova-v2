"""Tests for portfolio synthesis helpers in service.py."""
from app.pricing_v2.service import prepare_synthesis_input


def test_synthesis_input_truncation():
    items = [
        {
            "title": f"Eq {i}",
            "structured": {
                "valuation": {"fmv_low": 1000 * i, "fmv_high": 2000 * i, "currency": "CAD"},
                "comparables": [{"title": f"C{i}", "price": 1500 * i}],
            },
        }
        for i in range(200)
    ]
    text = prepare_synthesis_input(items)
    assert len(text) < 200_000  # ~50K tokens


def test_synthesis_input_structure():
    items = [
        {
            "title": "Test",
            "structured": {
                "valuation": {"fmv_low": 100, "fmv_high": 200, "currency": "USD"},
                "risks": ["Risk 1", "Risk 2"],
                "comparables": [{"t": 1}, {"t": 2}],
            },
        }
    ]
    import json

    parsed = json.loads(prepare_synthesis_input(items))
    assert parsed[0]["title"] == "Test"
    assert parsed[0]["currency"] == "USD"
    assert parsed[0]["comps_count"] == 2
