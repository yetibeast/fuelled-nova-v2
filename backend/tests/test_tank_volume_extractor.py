"""Tests for the tank-aware BBL volume extractor.

Used by the Tier 2.5 bulk runner to pull tank size out of unstructured
listing titles and descriptions before invoking the RCN engine.
"""
from __future__ import annotations

import pytest

from app.pricing_v2.equipment.parsing import extract_tank_volume_bbl


class TestExtractTankVolumeBBL:
    def test_simple_bbl(self):
        assert extract_tank_volume_bbl("400 BBL Storage Tank") == pytest.approx(400)

    def test_lowercase(self):
        assert extract_tank_volume_bbl("400 bbl storage tank") == pytest.approx(400)

    def test_no_space(self):
        assert extract_tank_volume_bbl("400BBL Storage Tank") == pytest.approx(400)

    def test_thousand_separator(self):
        assert extract_tank_volume_bbl("1,000 BBL Production Tank") == pytest.approx(1000)
        assert extract_tank_volume_bbl("10,000 BBL NGL Tank") == pytest.approx(10000)

    def test_decimal(self):
        # Rare but possible: "100.5 BBL"
        assert extract_tank_volume_bbl("100.5 BBL Tank") == pytest.approx(100.5)

    def test_with_description_prefix(self):
        title = "UNUSED 500 BBL Storage Tank, Coated, Argo"
        assert extract_tank_volume_bbl(title) == pytest.approx(500)

    def test_m3_fallback(self):
        # 50 m³ × 6.29 ≈ 314.5 BBL
        result = extract_tank_volume_bbl("50 m³ Storage Tank")
        assert result == pytest.approx(50 * 6.29, rel=0.001)

    def test_m3_with_caret(self):
        # Some titles use "m^3" or "m3"
        result = extract_tank_volume_bbl("50 m3 Storage Tank")
        assert result == pytest.approx(50 * 6.29, rel=0.001)

    def test_bbl_takes_precedence_over_m3(self):
        # If both present, BBL wins (it's the explicit oilfield unit).
        result = extract_tank_volume_bbl("400 BBL / 64 m³ Production Tank")
        assert result == pytest.approx(400)

    def test_no_volume_returns_none(self):
        assert extract_tank_volume_bbl("Storage Tank, Coated") is None

    def test_empty_string(self):
        assert extract_tank_volume_bbl("") is None

    def test_none_input(self):
        assert extract_tank_volume_bbl(None) is None

    def test_ignores_year_like_numbers(self):
        # "2010 400 BBL Tank" should extract 400, not 2010.
        assert extract_tank_volume_bbl("2010 400 BBL Tank") == pytest.approx(400)

    def test_uppercase_bbl(self):
        assert extract_tank_volume_bbl("400 BBL TANK") == pytest.approx(400)

    def test_bbl_with_period_after(self):
        # "400 BBL." — trailing punctuation
        assert extract_tank_volume_bbl("400 BBL. Storage Tank") == pytest.approx(400)
