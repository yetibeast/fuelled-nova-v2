"""Tests for market adjustment factors — NACE, H2S, material, geography, WTI heat.

These factors adjust FMV based on real-world market conditions.
"""
import pytest

from app.pricing_v2.rcn_engine.market_factors import (
    get_drive_factor,
    get_geography_factor,
    get_h2s_age_multiplier,
    get_market_heat_factor,
    get_material_factor,
    get_nace_premium,
)


# ── NACE compliance premium ───────────────────────────────────────────


class TestGetNacePremium:
    def test_not_nace_always_1(self):
        assert get_nace_premium("compressor_package", False) == pytest.approx(1.0)
        assert get_nace_premium("separator", False) == pytest.approx(1.0)

    def test_compressor_nace_premium(self):
        assert get_nace_premium("compressor_package", True) == pytest.approx(1.20)

    def test_separator_nace_premium(self):
        assert get_nace_premium("separator", True) == pytest.approx(1.18)

    def test_truck_no_nace_benefit(self):
        assert get_nace_premium("truck", True) == pytest.approx(1.0)

    def test_unknown_category_gets_default_premium(self):
        assert get_nace_premium("spaceship", True) == pytest.approx(1.15)


# ── H2S age multiplier ───────────────────────────────────────────────


class TestGetH2sAgeMultiplier:
    def test_no_exposure_is_1(self):
        assert get_h2s_age_multiplier(0, True) == pytest.approx(1.0)
        assert get_h2s_age_multiplier(0, False) == pytest.approx(1.0)
        assert get_h2s_age_multiplier(None, False) == pytest.approx(1.0)

    def test_nace_compliant_is_less_severe(self):
        nace = get_h2s_age_multiplier(5, True)
        non_nace = get_h2s_age_multiplier(5, False)
        assert nace < non_nace

    def test_nace_compliant_progression(self):
        # 0-5 years: 1.0 + 0.02*years
        assert get_h2s_age_multiplier(3, True) == pytest.approx(1.06)
        assert get_h2s_age_multiplier(5, True) == pytest.approx(1.10)
        # 5-15 years: 1.10 + 0.02*(years-5)
        assert get_h2s_age_multiplier(10, True) == pytest.approx(1.20)
        # 15+ years: 1.30 + 0.01*(years-15), capped at 1.50
        assert get_h2s_age_multiplier(20, True) == pytest.approx(1.35)

    def test_non_nace_progression(self):
        # 0-3 years: 1.0 + 0.10*years
        assert get_h2s_age_multiplier(2, False) == pytest.approx(1.20)
        assert get_h2s_age_multiplier(3, False) == pytest.approx(1.30)
        # 3-10 years: 1.30 + 0.05*(years-3)
        assert get_h2s_age_multiplier(7, False) == pytest.approx(1.50)
        # 10+ years: 1.65 + 0.03*(years-10), capped at 2.00
        assert get_h2s_age_multiplier(15, False) == pytest.approx(1.80)

    def test_capped_at_maximum(self):
        assert get_h2s_age_multiplier(100, True) <= 1.50
        assert get_h2s_age_multiplier(100, False) <= 2.00

    def test_multiplier_monotonically_increases(self):
        for nace in (True, False):
            prev = get_h2s_age_multiplier(0, nace)
            for years in range(1, 50):
                current = get_h2s_age_multiplier(years, nace)
                assert current >= prev - 1e-9, (
                    f"nace={nace}, years={years}: {current} < {prev}"
                )
                prev = current


# ── Material factor ───────────────────────────────────────────────────


class TestGetMaterialFactor:
    def test_carbon_steel_is_baseline(self):
        assert get_material_factor("carbon") == pytest.approx(1.0)
        assert get_material_factor("carbon_steel") == pytest.approx(1.0)

    def test_exotic_materials_premium(self):
        assert get_material_factor("stainless") == pytest.approx(2.5)
        assert get_material_factor("duplex") == pytest.approx(3.0)
        assert get_material_factor("inconel") == pytest.approx(4.0)

    def test_unknown_is_baseline(self):
        assert get_material_factor(None) == pytest.approx(1.0)
        assert get_material_factor("unobtanium") == pytest.approx(1.0)


# ── Drive type factor ─────────────────────────────────────────────────


class TestGetDriveFactor:
    def test_electric_is_baseline(self):
        assert get_drive_factor("electric") == pytest.approx(1.0)

    def test_gas_engine_premium(self):
        assert get_drive_factor("gas_engine") == pytest.approx(1.15)
        assert get_drive_factor("natural_gas") == pytest.approx(1.15)

    def test_diesel_premium(self):
        assert get_drive_factor("diesel") == pytest.approx(1.10)

    def test_unknown_is_baseline(self):
        assert get_drive_factor(None) == pytest.approx(1.0)


# ── Geography factor ──────────────────────────────────────────────────


class TestGetGeographyFactor:
    def test_premium_regions(self):
        assert get_geography_factor("permian") == pytest.approx(1.12)
        assert get_geography_factor("texas") == pytest.approx(1.08)
        assert get_geography_factor("alberta") == pytest.approx(1.05)

    def test_discount_regions(self):
        assert get_geography_factor("appalachian") == pytest.approx(0.92)
        assert get_geography_factor("latin_america") == pytest.approx(0.88)
        assert get_geography_factor("northern_bc") == pytest.approx(0.90)

    def test_abbreviations_work(self):
        assert get_geography_factor("ab") == pytest.approx(1.05)
        assert get_geography_factor("tx") == pytest.approx(1.08)
        assert get_geography_factor("bc") == pytest.approx(0.98)

    def test_unknown_region_is_neutral(self):
        assert get_geography_factor(None) == pytest.approx(1.0)
        assert get_geography_factor("mars") == pytest.approx(1.0)


# ── WTI market heat factor ───────────────────────────────────────────


class TestGetMarketHeatFactor:
    def test_neutral_wti_range(self):
        # $60-80 → raw_heat = 1.0 → factor = 1.0 regardless of category
        assert get_market_heat_factor(70, "compressor") == pytest.approx(1.0)
        assert get_market_heat_factor(60, "compressor") == pytest.approx(1.0)

    def test_high_wti_boosts_oil_sensitive_categories(self):
        factor = get_market_heat_factor(100, "compressor")  # sensitivity=1.0
        assert factor > 1.0

    def test_low_wti_depresses_oil_sensitive_categories(self):
        factor = get_market_heat_factor(40, "compressor")  # sensitivity=1.0
        assert factor < 1.0

    def test_low_sensitivity_categories_less_affected(self):
        # Loader has 0.2 sensitivity, compressor has 1.0
        loader = get_market_heat_factor(100, "loader")
        compressor = get_market_heat_factor(100, "compressor")
        # Both above 1.0 but loader much closer to 1.0
        assert 1.0 < loader < compressor

    def test_none_wti_uses_static_fallback(self):
        assert get_market_heat_factor(None, "compressor") == pytest.approx(1.05)
        assert get_market_heat_factor(None, "generator") == pytest.approx(1.00)

    def test_very_low_wti_has_floor(self):
        factor = get_market_heat_factor(10, "compressor")
        assert factor >= 0.50
