"""Integration tests for the full RCN calculator — FMV pipeline.

These tests verify business-critical invariants:
- Older equipment is worth less than newer
- Better condition commands higher price
- NACE compliance adds premium
- H2S exposure reduces value
- Known specs increase confidence
"""
import pytest

from app.pricing_v2.rcn_engine.calculator import calculate_rcn, RCNResult


# ── Basic sanity ──────────────────────────────────────────────────────


class TestCalculateRCNBasic:
    def test_returns_rcn_result(self):
        result = calculate_rcn("compressor", {"year": 2020, "current_year": 2026, "horsepower": 400})
        assert isinstance(result, RCNResult)
        assert result.fair_market_value > 0
        assert result.rcn > 0
        assert 0.1 <= result.confidence <= 1.0

    def test_minimal_input_does_not_crash(self):
        result = calculate_rcn("compressor", {})
        assert result.fair_market_value >= 0
        assert result.confidence > 0

    def test_unknown_category_uses_default_curve(self):
        result = calculate_rcn("unknown_widget", {"year": 2020, "current_year": 2026})
        assert result.depreciation_curve_used == "heavy_equip"


# ── Value ordering invariants ─────────────────────────────────────────


class TestValueOrdering:
    """Business rules: these must always hold regardless of implementation."""

    def test_older_equipment_worth_less(self):
        new = calculate_rcn("compressor", {"year": 2024, "current_year": 2026, "horsepower": 400})
        old = calculate_rcn("compressor", {"year": 2010, "current_year": 2026, "horsepower": 400})
        assert new.fair_market_value > old.fair_market_value

    def test_excellent_condition_worth_more_than_poor(self):
        excellent = calculate_rcn("pump", {
            "year": 2018, "current_year": 2026, "horsepower": 200, "condition": "excellent",
        })
        poor = calculate_rcn("pump", {
            "year": 2018, "current_year": 2026, "horsepower": 200, "condition": "poor",
        })
        assert excellent.fair_market_value > poor.fair_market_value

    def test_larger_hp_worth_more(self):
        small = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 100,
        })
        large = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 800,
        })
        assert large.fair_market_value > small.fair_market_value

    def test_nace_premium_increases_value(self):
        standard = calculate_rcn("separator", {
            "year": 2020, "current_year": 2026, "is_nace_compliant": False,
        })
        nace = calculate_rcn("separator", {
            "year": 2020, "current_year": 2026, "is_nace_compliant": True,
        })
        assert nace.rcn > standard.rcn
        assert nace.factors_applied["nace_premium"] > 1.0

    def test_h2s_exposure_reduces_value(self):
        clean = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400, "years_h2s_exposure": 0,
        })
        sour = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400, "years_h2s_exposure": 10,
        })
        assert clean.fair_market_value >= sour.fair_market_value

    def test_premium_material_increases_value(self):
        carbon = calculate_rcn("separator", {
            "year": 2020, "current_year": 2026, "material": "carbon",
        })
        stainless = calculate_rcn("separator", {
            "year": 2020, "current_year": 2026, "material": "stainless",
        })
        assert stainless.fair_market_value > carbon.fair_market_value

    def test_premium_region_increases_value(self):
        neutral = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400,
        })
        permian = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400, "region": "permian",
        })
        assert permian.fair_market_value > neutral.fair_market_value


# ── Confidence ordering ───────────────────────────────────────────────


class TestConfidenceOrdering:
    def test_more_data_means_higher_confidence(self):
        sparse = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026,
        })
        rich = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026,
            "horsepower": 400, "condition": "good", "hours": 12000,
            "comparable_count": 30, "comparable_cv": 0.3, "data_age_days": 15,
        })
        assert rich.confidence > sparse.confidence

    def test_minimal_input_has_low_confidence(self):
        result = calculate_rcn("compressor", {})
        assert result.confidence < 0.5


# ── Field aliases ─────────────────────────────────────────────────────


class TestFieldAliases:
    def test_hp_alias(self):
        result = calculate_rcn("compressor", {
            "hp": 400, "year": 2020, "current_year": 2026,
        })
        assert result.factors_applied["rcn_base"] > 100_000  # scaled by HP

    def test_location_alias(self):
        result = calculate_rcn("compressor", {
            "location": "permian", "year": 2020, "current_year": 2026,
        })
        assert result.factors_applied["geography_factor"] == pytest.approx(1.12)

    def test_nace_compliant_alias(self):
        result = calculate_rcn("separator", {
            "nace_compliant": True, "year": 2020, "current_year": 2026,
        })
        assert result.factors_applied["nace_premium"] > 1.0


# ── Factor traceability ──────────────────────────────────────────────


class TestFactorTraceability:
    """Every factor in the formula should be traceable in factors_applied."""

    def test_all_factors_present(self):
        result = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400,
            "condition": "good", "is_nace_compliant": True,
            "material": "stainless", "drive_type": "gas_engine",
            "region": "permian", "wti_price": 85,
        })
        factors = result.factors_applied
        expected_keys = {
            "category_key", "chronological_age", "effective_age",
            "effective_age_sour", "h2s_age_multiplier", "condition_tier",
            "rcn_base", "nace_premium", "material_factor", "drive_factor",
            "spec_modifiers_factor", "rcn_adjusted", "age_factor",
            "condition_factor", "market_heat", "geography_factor",
            "confidence_breakdown",
        }
        assert expected_keys.issubset(set(factors.keys()))

    def test_fmv_matches_formula(self):
        """FMV = RCN_adj x age_factor x condition_factor x market_heat x geo_factor."""
        result = calculate_rcn("compressor", {
            "year": 2020, "current_year": 2026, "horsepower": 400, "condition": "good",
        })
        f = result.factors_applied
        expected_fmv = (
            f["rcn_adjusted"]
            * f["age_factor"]
            * f["condition_factor"]
            * f["market_heat"]
            * f["geography_factor"]
        )
        assert result.fair_market_value == pytest.approx(expected_fmv, rel=0.01)
