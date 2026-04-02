"""Tests for Tier 3 report generation with new structured sections."""
from io import BytesIO
from docx import Document
from app.pricing_v2.report import generate_report


def _doc_text(result_bytes: bytes) -> str:
    """Extract all text from a generated docx as a single string."""
    doc = Document(BytesIO(result_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def test_report_with_all_new_sections():
    structured = {
        "valuation": {"fmv_low": 25000, "fmv_high": 40000, "confidence": "HIGH", "currency": "CAD", "rcn": 300000, "list_price": 46000, "walkaway": 21000},
        "comparables": [{"title": "Test comp", "price": 30000, "source": "Fuelled", "url": "https://fuelled.com/123", "notes": "Good condition"}],
        "risks": ["PLC obsolescence"],
        "market_context": "Strong demand in Montney region",
        "equipment_context": "JGP frame uncommon in new builds",
        "condition_assessment": "Needs frame overhaul, engine serviceable",
        "cost_considerations": "Transport $8K-$15K from Saskatchewan",
        "scenario_analysis": "As-is $25K-$40K, post-overhaul $45K-$60K",
        "marketing_guidance": "Lead with low hours in listing title",
        "missing_data_impact": "No serial number — cannot verify maintenance history",
        "key_value_drivers": ["Strong comps from same operator", "Active market"],
        "assumptions": ["Condition assumed B based on photos", "Hours as reported, not verified"],
        "sources": ["Fuelled.com #123", "Operator-provided specs"],
    }
    result = generate_report(structured, "Full analysis text here", "2019 Ariel JGK/4 800HP")
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'
    assert len(result) > 5000

    text = _doc_text(result)
    # Verify new sections appear
    assert "MARKET CONTEXT" in text
    assert "Strong demand in Montney region" in text
    assert "EQUIPMENT CONTEXT" in text
    assert "JGP frame uncommon in new builds" in text
    assert "CONDITION ASSESSMENT" in text
    assert "Needs frame overhaul" in text
    assert "COST CONSIDERATIONS" in text
    assert "Transport $8K-$15K" in text
    assert "SCENARIO ANALYSIS" in text
    assert "post-overhaul $45K-$60K" in text
    assert "MARKETING GUIDANCE" in text
    assert "Lead with low hours" in text
    assert "MISSING DATA IMPACT" in text
    assert "No serial number" in text
    # Sources as bullets
    assert "Fuelled.com #123" in text
    assert "Operator-provided specs" in text
    # Custom assumptions replace boilerplate
    assert "Condition assumed B based on photos" in text
    assert "Hours as reported, not verified" in text


def test_report_usd_currency():
    structured = {"valuation": {"fmv_low": 50000, "fmv_high": 80000, "confidence": "MEDIUM", "currency": "USD"}, "comparables": []}
    result = generate_report(structured, "US valuation", "2020 compressor in Texas")
    assert isinstance(result, bytes)
    text = _doc_text(result)
    assert "USD" in text


def test_report_minimal_data():
    structured = {"valuation": {"fmv_low": 10000, "fmv_high": 20000, "confidence": "LOW", "currency": "CAD"}}
    result = generate_report(structured, "Basic valuation", "Old separator")
    assert isinstance(result, bytes)
    text = _doc_text(result)
    # New optional sections should NOT appear when data is absent
    assert "MARKET CONTEXT" not in text
    assert "EQUIPMENT CONTEXT" not in text
    assert "SCENARIO ANALYSIS" not in text
