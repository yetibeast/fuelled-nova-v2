"""Tests for depreciation curves — age factors, effective age, curve mapping.

These tests serve as a baseline to verify the correctness of equipment
depreciation logic. Any regression here directly impacts FMV calculations.
"""
import pytest

from app.pricing_v2.rcn_engine.depreciation import (
    ANNUAL_HOURS,
    CONDITION_AGE_FACTOR,
    compute_effective_age,
    get_age_factor,
    get_curve_name,
)


# ── Curve name resolution ────────────────────────────────────────────


class TestGetCurveName:
    """Maps category strings to depreciation curve keys."""

    def test_exact_curve_names(self):
        for curve in ("compressor", "separator", "tank", "pump", "generator",
                      "pump_jack", "electrical", "treater", "heavy_equip", "truck"):
            assert get_curve_name(curve) == curve

    def test_alias_mapping(self):
        assert get_curve_name("compressor_package") == "compressor"
        assert get_curve_name("vessel") == "separator"
        assert get_curve_name("beam_pump") == "pump_jack"
        assert get_curve_name("e_house") == "electrical"
        assert get_curve_name("mcc") == "electrical"
        assert get_curve_name("vfd") == "electrical"
        assert get_curve_name("loader") == "heavy_equip"
        assert get_curve_name("excavator") == "heavy_equip"
        assert get_curve_name("trailer") == "truck"

    def test_whitespace_and_case_normalization(self):
        assert get_curve_name("  Compressor  ") == "compressor"
        assert get_curve_name("PUMP JACK") == "pump_jack"
        assert get_curve_name("Heavy-Equip") == "heavy_equip"
        assert get_curve_name("pump_jack") == "pump_jack"

    def test_unknown_returns_default(self):
        assert get_curve_name("spaceship") == "heavy_equip"
        assert get_curve_name("") == "heavy_equip"
        assert get_curve_name(None) == "heavy_equip"

    def test_meter_run_aliases_to_treater(self):
        """Tier 2.5: meter runs age like static utility equipment (treater curve).

        Anchored on the scoping report (2026-05-27): no corpus signal to
        calibrate a meter-specific curve, so we alias to treater — same
        pressure-tested static-equipment service life profile.
        """
        assert get_curve_name("meter_run") == "treater"
        assert get_curve_name("meter run") == "treater"
        assert get_curve_name("metering") == "treater"
        assert get_curve_name("metering equipment") == "treater"


# ── Effective age computation ─────────────────────────────────────────


class TestComputeEffectiveAge:
    """Blends chronological age, hours, and condition into effective age."""

    def test_hours_close_to_chronological_age(self):
        # 6000 hrs on compressor (6000 annual) → 1yr implied, chrono=1
        # divergence = 0 → 50/50 blend
        result = compute_effective_age(1, 6000, "GOOD", "compressor")
        assert result == pytest.approx(1.0)

    def test_hours_divergent_from_chronological_age(self):
        # 30000 hrs on compressor (6000 annual) → 5yr implied, chrono=1
        # divergence = 4.0 > 0.5 → 70/30 blend toward hours
        result = compute_effective_age(1, 30000, "GOOD", "compressor")
        expected = (0.7 * 5.0) + (0.3 * 1.0)  # 3.8
        assert result == pytest.approx(expected)

    def test_zero_hours_falls_through_to_condition(self):
        # hours=0 is treated as "no hours data"
        result = compute_effective_age(10, 0, "EXCELLENT", "compressor")
        assert result == pytest.approx(10 * CONDITION_AGE_FACTOR["EXCELLENT"])

    def test_no_hours_excellent_condition(self):
        result = compute_effective_age(10, None, "EXCELLENT", "compressor")
        assert result == pytest.approx(7.0)  # 10 * 0.7

    def test_no_hours_poor_condition(self):
        result = compute_effective_age(10, None, "POOR", "compressor")
        assert result == pytest.approx(14.0)  # 10 * 1.4

    def test_no_hours_scrap_condition(self):
        result = compute_effective_age(10, None, "SCRAP", "compressor")
        assert result == pytest.approx(20.0)  # 10 * 2.0

    def test_no_hours_no_condition(self):
        result = compute_effective_age(10, None, None, "compressor")
        assert result == pytest.approx(10.0)  # raw chronological

    def test_negative_age_clamped_to_zero(self):
        assert compute_effective_age(-5, None, None, "compressor") == pytest.approx(0.0)

    def test_different_categories_have_different_annual_hours(self):
        # Same hours, different categories → different implied age
        # Use hours that exceed expected utilization so the implied-age signal
        # dominates (avoids the chronological floor introduced for the
        # hours-inversion fix).
        heavy = compute_effective_age(5, 30000, "GOOD", "heavy_equip")  # 1500 annual → 20yr
        comp = compute_effective_age(5, 30000, "GOOD", "compressor")    # 6000 annual → 5yr
        assert heavy != comp

    # ── Regression: "hours-inversion" bug (Shawn Krienke, 2026-04-28) ────
    # Adding reported hours to an old unit must never make it appear younger
    # or worth more than the same unit with no hours data. The previous
    # formula blended hour-implied age with chronological age, so a 24-year
    # compressor with 61,000 hours got a *lower* effective age than the
    # same compressor with no hours, doubling its valuation.

    def test_hours_never_reduce_effective_age_below_chronological(self):
        # Shawn's listing: 24yr compressor, 61,000 hours
        eff_no_hours = compute_effective_age(24, None, "GOOD", "compressor")
        eff_with_hours = compute_effective_age(24, 61_000, "GOOD", "compressor")
        assert eff_with_hours >= eff_no_hours, (
            f"Adding 61,000 hours to a 24yr compressor must not make it appear younger. "
            f"Got: no_hours={eff_no_hours:.2f}yr, with_hours={eff_with_hours:.2f}yr"
        )

    def test_age_factor_monotonic_in_hours_at_fixed_chronological_age(self):
        """For a given chronological age, more hours must never increase value."""
        from app.pricing_v2.rcn_engine.depreciation import get_age_factor
        chrono = 24
        prev_factor = get_age_factor(
            compute_effective_age(chrono, None, "GOOD", "compressor"), "compressor"
        )
        for hours in (5_000, 15_000, 30_000, 50_000, 61_000, 100_000, 150_000):
            eff = compute_effective_age(chrono, hours, "GOOD", "compressor")
            factor = get_age_factor(eff, "compressor")
            assert factor <= prev_factor + 1e-9, (
                f"Adding hours increased age_factor at age={chrono}, hours={hours}: "
                f"prev={prev_factor:.4f}, new={factor:.4f}"
            )
            prev_factor = factor


# ── Age factor (depreciation curve interpolation) ─────────────────────


class TestGetAgeFactor:
    """Milestone-based linear interpolation on category curves."""

    def test_brand_new_is_1(self):
        assert get_age_factor(0, "compressor") == pytest.approx(1.0)
        assert get_age_factor(0, "truck") == pytest.approx(1.0)

    def test_exact_milestones(self):
        assert get_age_factor(10, "compressor") == pytest.approx(0.59)
        assert get_age_factor(10, "pump") == pytest.approx(0.52)
        assert get_age_factor(10, "truck") == pytest.approx(0.52)

    def test_interpolated_midpoint(self):
        # compressor: (1, 0.94) to (3, 0.87) at age 2
        # ratio = 0.5 → 0.94 + 0.5*(0.87-0.94) = 0.905
        assert get_age_factor(2, "compressor") == pytest.approx(0.905)

    def test_beyond_max_milestone_returns_floor(self):
        assert get_age_factor(50, "compressor") == pytest.approx(0.12)
        assert get_age_factor(100, "tank") == pytest.approx(0.10)

    def test_age_factor_monotonically_decreasing(self):
        """Equipment should never appreciate with age."""
        for category in ("compressor", "separator", "tank", "pump",
                         "generator", "pump_jack", "truck"):
            prev = get_age_factor(0, category)
            for age in range(1, 40):
                current = get_age_factor(age, category)
                assert current <= prev + 1e-9, (
                    f"{category} at age {age}: {current} > {prev}"
                )
                prev = current

    def test_all_categories_have_positive_floor(self):
        """Even ancient equipment retains some salvage value."""
        for category in ("compressor", "separator", "tank", "pump",
                         "generator", "pump_jack", "truck"):
            assert get_age_factor(999, category) > 0
