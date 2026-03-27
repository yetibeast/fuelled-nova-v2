"""Tests for RCN base tables — category normalization, base RCN, spec modifiers."""
import pytest

from app.pricing_v2.rcn_engine.rcn_tables import (
    RCNInput,
    compute_base_rcn,
    compute_spec_modifiers_factor,
    normalize_category,
)


# ── Category normalization ────────────────────────────────────────────


class TestNormalizeCategory:
    def test_direct_mapping(self):
        assert normalize_category("compressor") == "compressor_package"
        assert normalize_category("separator") == "separator"
        assert normalize_category("pump") == "pump"

    def test_plurals(self):
        assert normalize_category("compressors") == "compressor_package"
        assert normalize_category("separators") == "separator"
        assert normalize_category("pumps") == "pump"
        assert normalize_category("tanks") == "tank"

    def test_aliases(self):
        assert normalize_category("vessel") == "vessel"
        assert normalize_category("production") == "treater"
        assert normalize_category("e_house") == "e_house"
        assert normalize_category("mcc") == "e_house"

    def test_normalization(self):
        assert normalize_category("  Compressor  ") == "compressor_package"
        assert normalize_category("Heavy-Construction") == "loader"

    def test_unknown_passes_through(self):
        assert normalize_category("spaceship") == "spaceship"


# ── Base RCN computation ──────────────────────────────────────────────


class TestComputeBaseRCN:
    def test_compressor_with_hp(self):
        specs = RCNInput(horsepower=400, equipment_type="reciprocating")
        rcn, quality, has_size = compute_base_rcn("compressor_package", specs)
        # 100000 * (400/100)^0.6
        assert rcn > 100_000
        assert quality == pytest.approx(0.80)
        assert has_size is True

    def test_compressor_without_hp(self):
        specs = RCNInput(equipment_type="reciprocating")
        rcn, quality, has_size = compute_base_rcn("compressor_package", specs)
        assert rcn == pytest.approx(100_000)
        assert quality == pytest.approx(0.60)
        assert has_size is False

    def test_compressor_unknown_type_lower_quality(self):
        specs = RCNInput(horsepower=400, equipment_type="turbo_whatsit")
        rcn, quality, _ = compute_base_rcn("compressor_package", specs)
        assert quality == pytest.approx(0.70)  # vs 0.80 for known type

    def test_separator_with_weight(self):
        specs = RCNInput(weight_lbs=20_000)
        rcn, quality, has_size = compute_base_rcn("separator", specs)
        # 130000 * (20000/10000)^0.85
        assert rcn > 130_000
        assert quality == pytest.approx(0.70)
        assert has_size is True

    def test_separator_without_weight(self):
        specs = RCNInput()
        rcn, quality, has_size = compute_base_rcn("separator", specs)
        assert rcn == pytest.approx(130_000)
        assert quality == pytest.approx(0.60)
        assert has_size is False

    def test_heavy_equip_categories(self):
        specs = RCNInput()
        rcn, _, _ = compute_base_rcn("loader", specs)
        assert rcn == pytest.approx(250_000)
        rcn, _, _ = compute_base_rcn("excavator", specs)
        assert rcn == pytest.approx(300_000)

    def test_truck_classes(self):
        specs = RCNInput(truck_class="class_8")
        rcn, _, _ = compute_base_rcn("truck", specs)
        assert rcn == pytest.approx(280_000)

        specs = RCNInput(truck_class="class_6_7")
        rcn, _, _ = compute_base_rcn("truck", specs)
        assert rcn == pytest.approx(150_000)

    def test_unknown_category_gets_default(self):
        specs = RCNInput()
        rcn, quality, _ = compute_base_rcn("spaceship", specs)
        assert rcn == pytest.approx(100_000)
        assert quality == pytest.approx(0.30)

    def test_hp_scaling_is_sublinear(self):
        """Doubling HP should NOT double RCN (exponent < 1)."""
        small = RCNInput(horsepower=100)
        big = RCNInput(horsepower=200)
        rcn_small, _, _ = compute_base_rcn("compressor_package", small)
        rcn_big, _, _ = compute_base_rcn("compressor_package", big)
        ratio = rcn_big / rcn_small
        assert 1.0 < ratio < 2.0


# ── Spec modifiers ────────────────────────────────────────────────────


class TestComputeSpecModifiersFactor:
    def test_none_returns_1(self):
        assert compute_spec_modifiers_factor(None) == pytest.approx(1.0)

    def test_dict_modifiers(self):
        mods = {"winterization": 1.05, "sound_attenuation": 1.03}
        result = compute_spec_modifiers_factor(mods)
        assert result == pytest.approx(1.05 * 1.03)

    def test_list_modifiers(self):
        mods = [1.05, 1.03, 1.10]
        result = compute_spec_modifiers_factor(mods)
        assert result == pytest.approx(1.05 * 1.03 * 1.10)

    def test_single_float_modifier(self):
        assert compute_spec_modifiers_factor(1.15) == pytest.approx(1.15)

    def test_zero_values_skipped(self):
        mods = {"a": 1.05, "b": 0, "c": 1.03}
        result = compute_spec_modifiers_factor(mods)
        assert result == pytest.approx(1.05 * 1.03)

    def test_negative_single_returns_1(self):
        assert compute_spec_modifiers_factor(-0.5) == pytest.approx(1.0)
