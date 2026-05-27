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
