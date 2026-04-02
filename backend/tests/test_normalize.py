"""Tests for structured output normalization."""

from app.pricing_v2.normalize import normalize_structured


def test_empty_input():
    """Empty dict gets all fields with sensible defaults."""
    result = normalize_structured({})

    # Top-level lists default to []
    assert result["comparables"] == []
    assert result["risks"] == []
    assert result["key_value_drivers"] == []
    assert result["assumptions"] == []
    assert result["sources"] == []

    # Top-level strings default to None
    assert result["market_context"] is None
    assert result["equipment_context"] is None
    assert result["condition_assessment"] is None
    assert result["cost_considerations"] is None
    assert result["scenario_analysis"] is None
    assert result["marketing_guidance"] is None
    assert result["missing_data_impact"] is None

    # Valuation is a dict with its own defaults
    v = result["valuation"]
    assert isinstance(v, dict)
    assert v["fmv_low"] is None
    assert v["fmv_high"] is None
    assert v["fmv_mid"] is None
    assert v["rcn"] is None
    assert v["confidence"] == "LOW"
    assert v["currency"] == "CAD"
    assert v["list_price"] is None
    assert v["walkaway"] is None
    assert v["factors"] == []
    assert v["type"] is None
    assert v["title"] is None


def test_full_input_unchanged():
    """Complete data passes through without modification."""
    full = {
        "valuation": {
            "fmv_low": 10000,
            "fmv_high": 20000,
            "fmv_mid": 15000,
            "rcn": 30000,
            "confidence": "HIGH",
            "currency": "USD",
            "list_price": 25000,
            "walkaway": 8000,
            "factors": ["age", "condition"],
            "type": "FMV",
            "title": "Compressor Valuation",
        },
        "comparables": [{"id": 1, "price": 12000}],
        "risks": [{"severity": "high", "desc": "corrosion"}],
        "market_context": "Strong demand",
        "equipment_context": "2018 Ariel JGK/4",
        "condition_assessment": "Good",
        "cost_considerations": "Transport $2k",
        "scenario_analysis": "Bull/bear cases",
        "marketing_guidance": "List at $22k",
        "missing_data_impact": "None",
        "key_value_drivers": ["low hours"],
        "assumptions": ["standard config"],
        "sources": ["IronPlanet"],
    }
    result = normalize_structured(full)
    assert result == full


def test_valuation_defaults():
    """Partial valuation gets missing fields filled in."""
    data = {"valuation": {"fmv_low": 5000, "fmv_high": 10000}}
    result = normalize_structured(data)

    v = result["valuation"]
    assert v["fmv_low"] == 5000
    assert v["fmv_high"] == 10000
    assert v["fmv_mid"] is None
    assert v["confidence"] == "LOW"
    assert v["currency"] == "CAD"
    assert v["factors"] == []


def test_currency_preserved():
    """Explicit currency value is not overwritten by default."""
    data = {"valuation": {"currency": "USD"}}
    result = normalize_structured(data)
    assert result["valuation"]["currency"] == "USD"
