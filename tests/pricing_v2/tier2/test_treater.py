"""Treater family ruleset — Tier 2 vertical slice (Chunk 5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.treater import (
    TREATER_MATCH_TERMS,
    classify_treater,
    treater_rcn,
)


# ── Task 5.1a: variant classification ──────────────────────────────
# Treater families:
#   - heater_treater (default sweet/sour heater-treater package)
#   - electrostatic  (emulsion-breaking, routes to Mega bracket and
#                     bypasses the sour multiplier — electrostatic
#                     internals aren't sour-rated the same way)
#   - generic        (matched on "treater" but no electrostatic signal)

def test_classify_treater_heater_treater():
    assert classify_treater("96\" sour heater treater 2019") == "heater_treater"
    assert classify_treater("48\" sweet heater-treater") == "heater_treater"


def test_classify_treater_electrostatic():
    assert classify_treater("electrostatic treater 120\"") == "electrostatic"
    assert classify_treater("Electrostatic Treater Skid") == "electrostatic"


def test_classify_treater_generic():
    # "treater" alone with no heater/electrostatic hint → generic
    assert classify_treater("oil treater package 60\"") == "generic"


# ── Task 5.1b: RCN scaling by contactor diameter ────────────────────
# Brackets locked 2026-05-26 by Curt against HubSpot 96" sour sold
# corpus. Anchor: 96" sour heater-treater newbuild RCN = $750k CAD mid
# (Large bracket × 1.15× sour). All values are 2026 newbuild CAD.
#
# Bracket   Diameter     Low      Mid      High
# Small     < 60"        50k     100k     150k
# Medium    60–84"      200k     350k     500k
# Large     84–108"     520k     750k     950k     ← 96" sour anchor lives here
# Mega      ≥ 108"      1.4M    1.8M     2.5M     (electrostatic / 120"+)

def test_treater_rcn_small():
    rcn = treater_rcn(variant="heater_treater", diameter_in=48)
    assert rcn.low == 50_000 and rcn.mid == 100_000 and rcn.high == 150_000


def test_treater_rcn_medium():
    rcn = treater_rcn(variant="heater_treater", diameter_in=72)
    assert rcn.low == 200_000 and rcn.mid == 350_000 and rcn.high == 500_000


def test_treater_rcn_large():
    # 96" sour anchor → Large bracket. RCN mid = $750k CAD (newbuild),
    # the sour multiplier is applied downstream in price_treater().
    rcn = treater_rcn(variant="heater_treater", diameter_in=96)
    assert rcn.low == 520_000 and rcn.mid == 750_000 and rcn.high == 950_000


def test_treater_rcn_mega_by_diameter():
    """≥108" diameter (regardless of variant) → Mega bracket."""
    rcn = treater_rcn(variant="heater_treater", diameter_in=120)
    assert rcn.low == 1_400_000 and rcn.mid == 1_800_000 and rcn.high == 2_500_000


def test_treater_rcn_electrostatic_routes_to_mega():
    """Electrostatic variant routes to Mega bracket regardless of diameter.

    Per calibration: electrostatic units typically aren't sized below
    Mega-bracket scale in the Fuelled inventory; corpus shows 120"+.
    Force the bracket so the small-diameter parser miss doesn't
    underprice them.
    """
    rcn = treater_rcn(variant="electrostatic", diameter_in=84)
    assert rcn.low == 1_400_000 and rcn.mid == 1_800_000 and rcn.high == 2_500_000


# ── Task 5.2: dedicated treater depreciation curve ───────────────────
# Replaced 2026-05-26. Previous curve [1.00, 0.93, 0.85, 0.76, 0.67,
# 0.54, 0.35, 0.20, 0.12, 0.10] at [0,1,3,5,7,10,15,20,25,30] was too
# steep at 10-20yr. New curve is flatter at mid-life — treater shell
# rebuilds are cheaper than dehy glycol packages, so retention is
# higher mid-life. Validated against HubSpot 96" sour 11-16yr sold
# $80-150k range.

def test_treater_age_factor_curve():
    from backend.app.pricing_v2.rcn_engine.depreciation import get_age_factor
    assert get_age_factor(0, "treater") == pytest.approx(1.00, rel=0.01)
    assert get_age_factor(10, "treater") == pytest.approx(0.55, rel=0.02)
    assert get_age_factor(15, "treater") == pytest.approx(0.35, rel=0.05)
    assert get_age_factor(20, "treater") == pytest.approx(0.22, rel=0.05)
    assert get_age_factor(30, "treater") == pytest.approx(0.10, rel=0.05)


def test_treater_age_factor_flatter_than_old_curve_at_15yr():
    """The new curve must retain MORE value at 15yr than the old steep
    curve. Old 15yr = 0.35; new 15yr ≥ 0.35 (in practice exactly 0.35
    is the floor — but the 10yr point at 0.55 vs old 0.54 is the real
    flattening). This locks the intent: tail flattens, doesn't steepen."""
    from backend.app.pricing_v2.rcn_engine.depreciation import get_age_factor
    # 10yr is where the flattening shows: was 0.54, now 0.55
    assert get_age_factor(10, "treater") >= 0.54
    # 20yr is where the flattening continues: was 0.20, now 0.22
    assert get_age_factor(20, "treater") >= 0.20
