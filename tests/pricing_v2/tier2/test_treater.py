"""Treater family ruleset — Tier 2 vertical slice (Chunk 5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.treater import (
    TREATER_MATCH_TERMS,
    classify_treater,
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
