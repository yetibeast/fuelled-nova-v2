"""Heater family ruleset — Tier 2 vertical slice (Chunk 4).

Anchor: 2.0 MMBTU sour 1500# line heater newbuild RCN = $250k CAD mid
(Curt revised up from $235k after deep-dive calibration). See
`docs/tier2-calibration/heater-calibration-2026-05-26.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.heater import (
    HEATER_MATCH_TERMS,
    classify_heater,
    heater_code_stamp_adder,
    heater_pressure_adder,
    heater_rcn,
    heater_service_factor,
    parse_ansi_class,
    parse_mmbtu,
    price_heater,
)
from .test_column_spec import assert_row_satisfies_spec


# ── Task 4.1a: Variant classification ───────────────────────────────

def test_classify_heater_line():
    assert classify_heater("1.5 MMBTU 1500# Sour Line Heater") == "line_heater"
    assert classify_heater("indirect heater 2.0 MMBTU") == "line_heater"
    assert classify_heater("glycol bath heater 1500#") == "line_heater"
    assert classify_heater("water bath heater") == "line_heater"


def test_classify_heater_generic():
    # No explicit line/indirect/bath keyword still routes through heater
    # family (caller is responsible for upstream rejection of treaters
    # and frac heaters via the router).
    assert classify_heater("2.0 MMBTU heater package") == "generic"


# ── Task 4.1b: BTU/hr extraction ────────────────────────────────────

def test_parse_mmbtu_simple():
    mmbtu, parsed = parse_mmbtu("1.5 MMBTU 1500# Sour Line Heater")
    assert mmbtu == 1.5
    assert parsed is True


def test_parse_mmbtu_decimal_under_1():
    mmbtu, parsed = parse_mmbtu("0.75 MMBTU 2500# Sour Line Heater")
    assert mmbtu == 0.75
    assert parsed is True


def test_parse_mmbtu_no_signal_defaults():
    mmbtu, parsed = parse_mmbtu("line heater skid")
    # default falls in Medium bracket so unknown-size doesn't auto-cheap
    assert mmbtu == 1.5
    assert parsed is False


# ── Task 4.1c: ANSI / pressure parsing ──────────────────────────────

def test_parse_ansi_pound_notation():
    assert parse_ansi_class("3\" 1500# Sour Line Heater") == 1500
    assert parse_ansi_class("4\" 600# Sweet") == 600
    assert parse_ansi_class("2500# RTJ") == 2500


def test_parse_ansi_psi_notation():
    # PSI rating present, no class — convert to nearest class bucket
    assert parse_ansi_class("3000 PSI sour line heater") == 3000
    assert parse_ansi_class("10000 PSI line heater") == 10000


def test_parse_ansi_dual_rating_takes_higher():
    # "2500/600#" → use the higher rating (worst-case pressure)
    assert parse_ansi_class("3\" 2500/600# Sour Line Heater") == 2500


def test_parse_ansi_no_signal_returns_none():
    assert parse_ansi_class("line heater no specs") is None


# ── Task 4.1d: RCN brackets ─────────────────────────────────────────
# Locked by Curt 2026-05-26 after deep-dive. Anchor: 2.0 MMBTU sour
# 1500# newbuild RCN = $250k CAD mid.
#   Medium mid × pressure(1500=×1.10) × sour(×1.15) =
#     $180k × 1.10 × 1.15 = $227.7k  → close but Curt's anchor is $250k
#   Re-deriving: medium-mid needs to be $250k / 1.265 ≈ $198k; rounded
#   up to $200k for round-number presentation. Brackets land at:
#     Small  ≤1.0 MMBTU:    $45k / $70k / $100k
#     Medium 1.0-2.0 MMBTU: $110k / $180k / $250k
#     Large  2.0-3.5 MMBTU: $220k / $320k / $430k
#     Industrial 3.5-7.5:   $430k / $600k / $850k

def test_heater_rcn_small():
    rcn = heater_rcn(mmbtu=0.75)
    assert rcn.low == 45_000 and rcn.mid == 70_000 and rcn.high == 100_000


def test_heater_rcn_medium():
    rcn = heater_rcn(mmbtu=1.5)
    assert rcn.low == 110_000 and rcn.mid == 180_000 and rcn.high == 250_000


def test_heater_rcn_large():
    rcn = heater_rcn(mmbtu=3.0)
    assert rcn.low == 220_000 and rcn.mid == 320_000 and rcn.high == 430_000


def test_heater_rcn_industrial():
    rcn = heater_rcn(mmbtu=5.0)
    assert rcn.low == 430_000 and rcn.mid == 600_000 and rcn.high == 850_000


# ── Task 4.1e: pressure multiplier ──────────────────────────────────

def test_heater_pressure_adder_low():
    assert heater_pressure_adder(None) == 1.00
    assert heater_pressure_adder(150) == 1.00
    assert heater_pressure_adder(599) == 1.00


def test_heater_pressure_adder_medium():
    # <1500 → 1.10
    assert heater_pressure_adder(600) == 1.10
    assert heater_pressure_adder(900) == 1.10
    assert heater_pressure_adder(1499) == 1.10


def test_heater_pressure_adder_high():
    # <2500 → 1.20
    assert heater_pressure_adder(1500) == 1.20
    assert heater_pressure_adder(2499) == 1.20


def test_heater_pressure_adder_extreme():
    # ≥2500 → 1.30
    assert heater_pressure_adder(2500) == 1.30
    assert heater_pressure_adder(5000) == 1.30
    assert heater_pressure_adder(10000) == 1.30


# ── Task 4.1f: B149.3 / ABSA code-stamp adder ───────────────────────

def test_code_stamp_adder_b149_3():
    assert heater_code_stamp_adder("1.25 MMBTU B149.3 compliant line heater") == 1.20


def test_code_stamp_adder_absa():
    assert heater_code_stamp_adder("2.0 MMBTU ABSA A583633 line heater") == 1.20


def test_code_stamp_adder_csa_b149():
    assert heater_code_stamp_adder("CSA B149.3 line heater") == 1.20


def test_code_stamp_adder_code_stamped():
    assert heater_code_stamp_adder("code-stamped line heater") == 1.20
    assert heater_code_stamp_adder("code stamp registered unit") == 1.20


def test_code_stamp_adder_none():
    assert heater_code_stamp_adder("generic line heater") == 1.00


# ── Task 4.2: service factor (sweet vs sour) ────────────────────────

def test_heater_service_factor_sweet():
    assert heater_service_factor("sweet gas line heater") == 1.00


def test_heater_service_factor_sour():
    assert heater_service_factor("sour H2S line heater") == 1.15


# ── Task 4.3: dedicated heater depreciation curve ───────────────────
# Aliased to treater pre-Tier-2; deep-dive locked in a heater-specific
# curve sitting between treater (gentler) and dehydrator (steeper).

def test_heater_age_factor_dedicated_curve():
    from backend.app.pricing_v2.rcn_engine.depreciation import (
        AGE_CURVES,
        get_age_factor,
        get_curve_name,
    )
    # 1. The curve must exist as its own entry, not alias to treater
    assert "heater" in AGE_CURVES
    # 2. heater category resolves to heater (not treater)
    assert get_curve_name("heater") == "heater"
    # 3. line_heater still aliases to heater
    assert get_curve_name("line_heater") == "heater"
    # 4. milestone retention values match deep-dive locked spec
    assert get_age_factor(0, "heater") == pytest.approx(1.00, rel=0.01)
    assert get_age_factor(10, "heater") == pytest.approx(0.47, rel=0.05)
    assert get_age_factor(15, "heater") == pytest.approx(0.32, rel=0.05)
    assert get_age_factor(20, "heater") == pytest.approx(0.20, rel=0.05)


# ── Task 4.4: end-to-end pricing produces spec-compliant row ────────

def test_heater_end_to_end_2mmbtu_sour_1500():
    fx = json.loads(
        (Path(__file__).parent / "fixtures" / "heater_2mmbtu_sour_1500.json").read_text()
    )
    row = price_heater(fx)
    # 1. Spec contract holds
    assert_row_satisfies_spec(row)
    # 2. Family routed correctly (flat, not kebab)
    assert row.to_dict()["Family"] == "heater"
    # 3. Methodology path traceable to BTU + ANSI
    assert "mmbtu" in row.to_dict()["Methodology Path"].lower()
    # 4. Reasoning trail multi-line (≥3 lines)
    assert row.to_dict()["Reasoning Trail"].count("\n") >= 3
    # 5. Sold anchor not used in standalone run
    assert row.to_dict()["Sold Anchor Used"] is False
    # 6. Conf class consistent with composite
    d = row.to_dict()
    composite = d["Conf Composite"]
    cls = d["Conf Class"]
    if composite >= 0.75:
        assert cls == "automated"
    elif composite >= 0.40:
        assert cls == "hitl_review"
    else:
        assert cls == "manual"
    # 7. Price targets bracket the FMV mid
    fmv_mid = d["RCN New Mid"] * d["Factor Combined"]
    assert d["Price Target LOW"] < fmv_mid < d["Price Target HIGH"]


def test_heater_end_to_end_code_stamped_premium():
    """B149.3 / ABSA code-stamped line heater carries +20% RCN adder.

    Without the adder, the calibration deep-dive showed the model
    under-predicts code-stamped 1.25 MMBTU sour 1500# units by 38%.
    """
    base = json.loads(
        (Path(__file__).parent / "fixtures" / "heater_2mmbtu_sour_1500.json").read_text()
    )
    stamped = dict(base)
    stamped["listing_name"] = (
        base["listing_name"] + " B149.3 Compliant ABSA-Registered"
    )
    stamped["description"] = (
        base["description"] + " B149.3 code-stamped, ABSA serial A583633."
    )
    row_base = price_heater(base).to_dict()
    row_stamped = price_heater(stamped).to_dict()
    # Stamped RCN mid is exactly 20% higher than base
    assert row_stamped["RCN New Mid"] == pytest.approx(
        row_base["RCN New Mid"] * 1.20, rel=0.001
    )
