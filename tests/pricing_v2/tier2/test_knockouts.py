"""Knockout family ruleset — Tier 2 Chunk 3.

Covers the 4-way disambiguator (FWKO / Flare KO / Gas KO / Ambiguous),
per-sub-family RCN brackets, service factor, and end-to-end pricing.

Calibration locked 2026-05-27 by Curt — see
`backend/app/pricing_v2/tier2/knockouts.py` for the anchor notes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.knockouts import (
    KnockoutSubFamily,
    classify_knockout,
    flare_ko_rcn,
    fwko_rcn,
    gas_ko_rcn,
    knockout_service_factor,
    price_knockout,
)

from .test_column_spec import assert_row_satisfies_spec


# ── Task 3.2: Disambiguator ────────────────────────────────────────


@pytest.mark.parametrize("text,expected", [
    # FWKO — direct token
    ("48 inch FWKO vessel", "fwko"),
    ("free water knockout 60-inch", "fwko"),
    ("free-water knock out, internals included", "fwko"),
    # FWKO — category-based fallback (Separator/Vessel + "3-phase")
    # handled in test_classify_fwko_via_category below
    # Flare KO
    ("flare knockout drum", "flare"),
    ("flare KO drum 36 inch", "flare"),
    ("flare knock-out vessel", "flare"),
    # Gas KO
    ("gas knockout drum, compressor discharge", "gas"),
    ("inlet scrubber for gas service", "gas"),
    ("inlet KO 24 inch", "gas"),
    ("Gas KO drum, sweet", "gas"),
    # Ambiguous — catch-all
    ("KO drum", "ambiguous"),
    ("knockout drum 36 inch", "ambiguous"),
    ("slug catcher 48 inch", "ambiguous"),
])
def test_classify_knockout(text, expected):
    assert classify_knockout(text) == expected


def test_classify_knockout_fwko_via_category_three_phase():
    """Separator/Vessel category + '3-phase' in name → FWKO."""
    assert classify_knockout("36 inch 3-phase vessel", category="Separator") == "fwko"
    assert classify_knockout("3-phase production vessel", category="Vessel") == "fwko"
    # Without category, 3-phase alone is not a strong-enough FWKO signal
    assert classify_knockout("36 inch 3-phase vessel") == "ambiguous"


def test_classify_knockout_first_match_wins():
    """FWKO regex fires before Flare KO before Gas KO before Ambiguous."""
    # "FWKO" token present alongside "flare" wording → FWKO wins
    assert classify_knockout("FWKO drum sometimes seen at flare KO duty") == "fwko"
    # "flare KO" present alongside "inlet scrubber" → Flare wins
    assert classify_knockout("flare KO drum with inlet scrubber tie-in") == "flare"


def test_classify_knockout_case_insensitive():
    assert classify_knockout("FWKO") == "fwko"
    assert classify_knockout("fwko") == "fwko"
    assert classify_knockout("Free Water Knockout") == "fwko"
    assert classify_knockout("FLARE KO DRUM") == "flare"


# ── Task 3.3: FWKO RCN brackets (CAD, sweet base) ──────────────────


def test_fwko_rcn_small():
    """< 36" → Small bracket."""
    rcn = fwko_rcn(diameter_in=24.0)
    assert rcn.low == 50_000 and rcn.mid == 80_000 and rcn.high == 120_000


def test_fwko_rcn_medium():
    """36-60" → Medium bracket."""
    rcn = fwko_rcn(diameter_in=48.0)
    assert rcn.low == 140_000 and rcn.mid == 200_000 and rcn.high == 280_000


def test_fwko_rcn_large():
    """60-96" → Large bracket."""
    rcn = fwko_rcn(diameter_in=72.0)
    assert rcn.low == 300_000 and rcn.mid == 400_000 and rcn.high == 520_000


def test_fwko_rcn_xl():
    """≥96" → XL bracket."""
    rcn = fwko_rcn(diameter_in=120.0)
    assert rcn.low == 550_000 and rcn.mid == 700_000 and rcn.high == 900_000


def test_fwko_rcn_bracket_boundaries():
    """36" hits Medium (not Small); 60" hits Large; 96" hits XL."""
    assert fwko_rcn(diameter_in=36.0).mid == 200_000  # Medium
    assert fwko_rcn(diameter_in=60.0).mid == 400_000  # Large
    assert fwko_rcn(diameter_in=96.0).mid == 700_000  # XL


# ── Task 3.3: Flare KO RCN brackets ────────────────────────────────


def test_flare_ko_rcn_tiny():
    """< 36" → Tiny bracket."""
    rcn = flare_ko_rcn(diameter_in=24.0)
    assert rcn.low == 12_000 and rcn.mid == 18_000 and rcn.high == 25_000


def test_flare_ko_rcn_small():
    """36-60" → Small bracket."""
    rcn = flare_ko_rcn(diameter_in=48.0)
    assert rcn.low == 30_000 and rcn.mid == 45_000 and rcn.high == 60_000


def test_flare_ko_rcn_medium():
    """60-96" → Medium bracket."""
    rcn = flare_ko_rcn(diameter_in=72.0)
    assert rcn.low == 70_000 and rcn.mid == 100_000 and rcn.high == 140_000


def test_flare_ko_rcn_large():
    """≥96" → Large bracket."""
    rcn = flare_ko_rcn(diameter_in=120.0)
    assert rcn.low == 140_000 and rcn.mid == 200_000 and rcn.high == 270_000


# ── Task 3.4: Gas KO RCN brackets ──────────────────────────────────


def test_gas_ko_rcn_small():
    """< 24" → Small bracket."""
    rcn = gas_ko_rcn(diameter_in=16.0)
    assert rcn.low == 20_000 and rcn.mid == 30_000 and rcn.high == 45_000


def test_gas_ko_rcn_medium():
    """24-36" → Medium bracket."""
    rcn = gas_ko_rcn(diameter_in=30.0)
    assert rcn.low == 40_000 and rcn.mid == 55_000 and rcn.high == 75_000


def test_gas_ko_rcn_large():
    """≥36" → Large bracket."""
    rcn = gas_ko_rcn(diameter_in=48.0)
    assert rcn.low == 65_000 and rcn.mid == 85_000 and rcn.high == 110_000


# ── Service factor (sweet/sour) ───────────────────────────────────


def test_knockout_service_factor_sweet():
    assert knockout_service_factor("sweet gas service") == 1.00


def test_knockout_service_factor_sour():
    assert knockout_service_factor("sour gas H2S 2%") == 1.15
    assert knockout_service_factor("NACE H₂S service") == 1.15


# ── Task 3.5: End-to-end ─────────────────────────────────────────


def _load_fx(name: str) -> dict:
    return json.loads(
        (Path(__file__).parent / "fixtures" / name).read_text()
    )


def test_knockout_e2e_fwko():
    fx = _load_fx("knockout_fwko_48in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "knockout-fwko"
    assert "fwko" in d["Methodology Path"].lower()
    assert d["Depreciation Curve"] == "knockout_fwko"
    assert d["Review Flag"] is False
    assert d["Reasoning Trail"].count("\n") >= 3
    # Price targets bracket the FMV mid
    fmv_mid = d["RCN New Mid"] * d["Factor Combined"]
    assert d["Price Target LOW"] < fmv_mid < d["Price Target HIGH"]


def test_knockout_e2e_flare():
    fx = _load_fx("knockout_flare_48in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "knockout-flare"
    assert "flare" in d["Methodology Path"].lower()
    assert d["Depreciation Curve"] == "knockout_flare"
    assert d["Review Flag"] is False


def test_knockout_e2e_gas_data_thin_flag_in_trail():
    fx = _load_fx("knockout_gas_30in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "knockout-gas"
    assert "gas" in d["Methodology Path"].lower()
    # Gas KO is data-thin; reasoning trail must surface "validation pending"
    assert "validation pending" in d["Reasoning Trail"].lower()
    # Rides separator curve since no dedicated curve
    assert d["Depreciation Curve"] == "separator"


def test_knockout_e2e_ambiguous_flags_for_review():
    fx = _load_fx("knockout_ambiguous_36in.json")
    row = price_knockout(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "knockout-ambiguous"
    assert d["Review Flag"] is True
    assert "ambiguous" in d["Review Reason"].lower()
    # Bands must be widened ≥50% (per locked spec), not hidden
    spread = (d["Price Target HIGH"] - d["Price Target LOW"]) / d["Price Target MID"]
    assert spread >= 0.50


def test_knockout_e2e_sour_service_premium_applied():
    fx = _load_fx("knockout_fwko_48in.json")
    fx_sour = {**fx, "description": fx["description"] + " sour gas H2S service"}
    row_sweet = price_knockout(fx)
    row_sour = price_knockout(fx_sour)
    # Same listing, sour adds 15% — Factor Service captures it
    assert row_sour.to_dict()["Factor Service"] == pytest.approx(1.15)
    assert row_sweet.to_dict()["Factor Service"] == pytest.approx(1.00)
    # And combined factor reflects the premium
    assert (
        row_sour.to_dict()["Factor Combined"]
        > row_sweet.to_dict()["Factor Combined"]
    )
