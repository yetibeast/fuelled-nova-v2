"""Tests for condition normalization and condition factors.

Covers: marketplace string mapping, hours-based inference, factor lookup.
"""
import pytest

from app.pricing_v2.rcn_engine.condition import (
    get_condition_factor,
    infer_condition_from_hours,
    normalize_condition,
    CONDITION_FACTORS,
)


# ── Condition normalization ───────────────────────────────────────────


class TestNormalizeCondition:
    """Maps raw marketplace labels to standardized tiers."""

    @pytest.mark.parametrize("raw,expected", [
        ("excellent", "EXCELLENT"),
        ("very good", "VERY_GOOD"),
        ("good", "GOOD"),
        ("fair", "FAIR"),
        ("poor", "POOR"),
        ("scrap", "SCRAP"),
    ])
    def test_standard_labels(self, raw, expected):
        assert normalize_condition(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("new", "EXCELLENT"),
        ("new/unused", "EXCELLENT"),
        ("rebuilt", "GOOD"),
        ("refurbished", "GOOD"),
        ("reconditioned", "GOOD"),
        ("used", "GOOD"),
        ("used-b", "FAIR"),
        ("as-is", "FAIR"),
        ("as is", "FAIR"),
        ("salvage", "SCRAP"),
        ("parts only", "SCRAP"),
        ("for parts", "SCRAP"),
        ("inoperable", "SCRAP"),
        ("not running", "POOR"),
    ])
    def test_marketplace_aliases(self, raw, expected):
        assert normalize_condition(raw) == expected

    @pytest.mark.parametrize("status", ["active", "sold", "expired", "delisted", "pending"])
    def test_listing_statuses_default_to_good(self, status):
        assert normalize_condition(status) == "GOOD"

    def test_none_defaults_to_good(self):
        assert normalize_condition(None) == "GOOD"

    def test_empty_string_defaults_to_good(self):
        assert normalize_condition("") == "GOOD"

    def test_whitespace_normalization(self):
        assert normalize_condition("  very   good  ") == "VERY_GOOD"

    def test_case_insensitive(self):
        assert normalize_condition("EXCELLENT") == "EXCELLENT"
        assert normalize_condition("Excellent") == "EXCELLENT"
        assert normalize_condition("eXcElLeNt") == "EXCELLENT"

    def test_unknown_defaults_to_good(self):
        assert normalize_condition("pristine") == "GOOD"
        assert normalize_condition("like new but rusty") == "GOOD"


# ── Hours-based condition inference ───────────────────────────────────


class TestInferConditionFromHours:
    """Category-specific hour thresholds determine condition tier."""

    def test_compressor_tiers(self):
        assert infer_condition_from_hours(5_000, "compressor") == "EXCELLENT"
        assert infer_condition_from_hours(15_000, "compressor") == "VERY_GOOD"
        assert infer_condition_from_hours(35_000, "compressor") == "GOOD"
        assert infer_condition_from_hours(55_000, "compressor") == "FAIR"
        assert infer_condition_from_hours(70_000, "compressor") == "POOR"

    def test_heavy_equip_tiers(self):
        assert infer_condition_from_hours(1_000, "heavy_equip") == "EXCELLENT"
        assert infer_condition_from_hours(4_000, "heavy_equip") == "VERY_GOOD"
        assert infer_condition_from_hours(8_000, "heavy_equip") == "GOOD"
        assert infer_condition_from_hours(15_000, "heavy_equip") == "FAIR"
        assert infer_condition_from_hours(20_000, "heavy_equip") == "POOR"

    def test_exact_boundary_goes_to_next_tier(self):
        # At exactly the threshold → next tier (not less-than)
        assert infer_condition_from_hours(8_000, "compressor") == "VERY_GOOD"
        assert infer_condition_from_hours(7_999, "compressor") == "EXCELLENT"

    def test_none_hours_returns_none(self):
        assert infer_condition_from_hours(None, "compressor") is None

    def test_negative_hours_returns_none(self):
        assert infer_condition_from_hours(-100, "compressor") is None

    def test_zero_hours(self):
        assert infer_condition_from_hours(0, "compressor") is None

    def test_unknown_category_uses_compressor_fallback(self):
        assert infer_condition_from_hours(5_000, "spaceship") == "EXCELLENT"


# ── Condition factor lookup ───────────────────────────────────────────


class TestGetConditionFactor:
    """Returns depreciation multiplier for each condition tier."""

    @pytest.mark.parametrize("tier,factor", [
        ("EXCELLENT", 0.95),
        ("VERY_GOOD", 0.85),
        ("GOOD", 0.75),
        ("FAIR", 0.60),
        ("POOR", 0.40),
        ("SCRAP", 0.12),
    ])
    def test_all_tiers(self, tier, factor):
        assert get_condition_factor(tier) == pytest.approx(factor)

    def test_none_defaults_to_good(self):
        assert get_condition_factor(None) == pytest.approx(0.75)

    def test_unknown_defaults_to_good(self):
        assert get_condition_factor("UNKNOWN") == pytest.approx(0.75)

    def test_factors_are_monotonically_ordered(self):
        """Better condition should always give higher factor."""
        tiers = ["EXCELLENT", "VERY_GOOD", "GOOD", "FAIR", "POOR", "SCRAP"]
        factors = [CONDITION_FACTORS[t] for t in tiers]
        for i in range(len(factors) - 1):
            assert factors[i] > factors[i + 1], (
                f"{tiers[i]} ({factors[i]}) should be > {tiers[i+1]} ({factors[i+1]})"
            )
