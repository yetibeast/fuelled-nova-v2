"""Meter Run family — Tier 2.5 ruleset.

Pipe-size × ANSI bracket pricing with meter-type adders. LACT /
custody-transfer sub-flag routes to manual Tier 3 review.

Calibration anchor (2026-05-27): scoping report
`docs/tier2-calibration/tanks-meter-runs-scoping-2026-05-27.md`.
Brackets re-validated against HubSpot sold meter runs (n=175 sold,
median ask $750–$6,250 across 2-4" 600-ANSI plain meter runs); 2026
newbuild brackets × treater age curve × condition factor lands in
the right zip code.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.meter_run import (
    METER_RUN_MATCH_TERMS,
    classify_meter_run,
    detect_meter_type,
    is_lact_or_custody,
    meter_run_rcn,
    meter_run_service_factor,
    parse_meter_run_inputs,
    price_meter_run,
)
from .test_column_spec import assert_row_satisfies_spec


# ── Classifier: family match ──────────────────────────────────────

def test_classify_meter_run_matches_meter_run_phrase():
    assert classify_meter_run("4\" 600 ANSI Meter Run") is True
    assert classify_meter_run("Dual Meter Skid 2-inch") is True
    assert classify_meter_run("Metering Skid 3\"") is True
    assert classify_meter_run("Flow Meter Package") is True
    assert classify_meter_run("Flow Run Skid") is True


def test_classify_meter_run_excludes_unrelated():
    assert classify_meter_run("Compressor Package") is False
    assert classify_meter_run("Tank 400 BBL") is False
    assert classify_meter_run("TEG Dehydrator 5 MMSCFD") is False


# ── LACT / custody-transfer detection ─────────────────────────────

def test_is_lact_or_custody_positive():
    assert is_lact_or_custody("LACT Unit Skid") is True
    assert is_lact_or_custody("Custody Transfer Meter Run") is True
    assert is_lact_or_custody("Custody-Transfer Skid") is True
    assert is_lact_or_custody("Dual LACT Package w/ Control Room") is True


def test_is_lact_or_custody_negative():
    assert is_lact_or_custody("4\" 600 ANSI Meter Run") is False
    assert is_lact_or_custody("Metering Skid 3\"") is False


# ── Meter-type detection ──────────────────────────────────────────

def test_detect_meter_type_orifice_default():
    # Plain meter run with no type signal → orifice (1.00× baseline).
    assert detect_meter_type("4\" 600 ANSI Meter Run") == "orifice"


def test_detect_meter_type_turbine():
    assert detect_meter_type("3\" 600 Turbine Meter Skid") == "turbine"


def test_detect_meter_type_coriolis():
    assert detect_meter_type("2\" Micro Motion Coriolis Meter") == "coriolis"
    assert detect_meter_type("3\" Coriolis Mass Flow Meter") == "coriolis"


def test_detect_meter_type_ultrasonic():
    assert detect_meter_type("6\" Ultrasonic Flow Meter") == "ultrasonic"


def test_detect_meter_type_vortex():
    assert detect_meter_type("4\" Vortex Meter Run") == "vortex"


# ── Pipe size + ANSI parsing ──────────────────────────────────────

def test_parse_meter_run_inputs_pipe_size():
    out = parse_meter_run_inputs("4\" 600 ANSI Meter Run")
    assert out.pipe_size_in == 4
    assert out.ansi_class == 600


def test_parse_meter_run_inputs_smart_quote_pipe():
    # Listings often use smart-quote " instead of straight "
    out = parse_meter_run_inputs("3” 600 ANSI Meter Skid")
    assert out.pipe_size_in == 3
    assert out.ansi_class == 600


def test_parse_meter_run_inputs_missing_ansi_defaults_600():
    out = parse_meter_run_inputs("2\" Meter Run")
    assert out.pipe_size_in == 2
    assert out.ansi_class == 600  # default per scoping report (62% coverage; 600# most common)
    assert out.ansi_parsed is False


def test_parse_meter_run_inputs_missing_pipe_defaults_4():
    out = parse_meter_run_inputs("Metering Skid 600 ANSI")
    assert out.pipe_size_in == 4  # mid-size default
    assert out.pipe_parsed is False


def test_parse_meter_run_inputs_8in_capped_to_grid():
    # ≥8" all map to the 8" bracket.
    out = parse_meter_run_inputs("10\" 900 ANSI Meter Run")
    assert out.pipe_size_in == 10  # parsed value preserved; bracket lookup caps


def test_parse_meter_run_inputs_sour_flag():
    assert parse_meter_run_inputs("4\" 600 ANSI Sour Meter Run").is_sour is True
    assert parse_meter_run_inputs("3\" 600 NACE Meter Skid").is_sour is True
    assert parse_meter_run_inputs("4\" 600 ANSI Meter Run").is_sour is False


# ── RCN bracket lookup ────────────────────────────────────────────
# Brackets from scoping report 2026-05-27 (Curt-locked) — sweet base CAD,
# pipe size × ANSI class, low/mid/high triples.

def test_meter_run_rcn_2in_600_ansi_orifice():
    rcn = meter_run_rcn(pipe_size_in=2, ansi_class=600, meter_type="orifice", is_sour=False)
    assert rcn.low == 6_000 and rcn.mid == 10_000 and rcn.high == 14_000


def test_meter_run_rcn_4in_600_ansi_orifice():
    rcn = meter_run_rcn(pipe_size_in=4, ansi_class=600, meter_type="orifice", is_sour=False)
    assert rcn.low == 18_000 and rcn.mid == 28_000 and rcn.high == 39_000


def test_meter_run_rcn_6in_1500_ansi_orifice():
    rcn = meter_run_rcn(pipe_size_in=6, ansi_class=1500, meter_type="orifice", is_sour=False)
    assert rcn.low == 45_000 and rcn.mid == 68_000 and rcn.high == 92_000


def test_meter_run_rcn_8in_caps_high_bracket():
    """10\" listings still map to the ≥8\" bracket (highest pipe row)."""
    rcn_8 = meter_run_rcn(pipe_size_in=8, ansi_class=600, meter_type="orifice", is_sour=False)
    rcn_10 = meter_run_rcn(pipe_size_in=10, ansi_class=600, meter_type="orifice", is_sour=False)
    assert rcn_10.mid == rcn_8.mid


def test_meter_run_rcn_low_ansi_bracket():
    rcn = meter_run_rcn(pipe_size_in=2, ansi_class=150, meter_type="orifice", is_sour=False)
    assert rcn.low == 4_000 and rcn.mid == 7_000 and rcn.high == 10_000


def test_meter_run_rcn_coriolis_adder():
    base = meter_run_rcn(pipe_size_in=3, ansi_class=600, meter_type="orifice", is_sour=False)
    coriolis = meter_run_rcn(pipe_size_in=3, ansi_class=600, meter_type="coriolis", is_sour=False)
    assert coriolis.mid == int(round(base.mid * 1.40))


def test_meter_run_rcn_turbine_adder():
    base = meter_run_rcn(pipe_size_in=3, ansi_class=600, meter_type="orifice", is_sour=False)
    turbine = meter_run_rcn(pipe_size_in=3, ansi_class=600, meter_type="turbine", is_sour=False)
    assert turbine.mid == int(round(base.mid * 1.15))


def test_meter_run_rcn_sour_premium():
    sweet = meter_run_rcn(pipe_size_in=4, ansi_class=600, meter_type="orifice", is_sour=False)
    sour = meter_run_rcn(pipe_size_in=4, ansi_class=600, meter_type="orifice", is_sour=True)
    assert sour.mid == int(round(sweet.mid * 1.15))


# ── Service factor (matches dehydrator pattern) ───────────────────

def test_meter_run_service_factor_sweet():
    assert meter_run_service_factor("4\" 600 ANSI Meter Run") == 1.00


def test_meter_run_service_factor_sour():
    assert meter_run_service_factor("4\" 600 Sour Meter Run") == 1.15


# ── End-to-end pricing (spec-compliant row) ───────────────────────

def test_price_meter_run_end_to_end_4in_600():
    fx = json.loads(
        (Path(__file__).parent / "fixtures" / "meter_run_4in_600_orifice.json").read_text()
    )
    row = price_meter_run(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "meter-run"
    assert "meter-run" in d["Methodology Path"]
    assert d["Depreciation Curve"] == "treater"
    assert d["Reasoning Trail"].count("\n") >= 3
    # Price targets bracket the FMV mid
    fmv_mid = d["RCN New Mid"] * d["Factor Combined"]
    assert d["Price Target LOW"] < fmv_mid < d["Price Target HIGH"]
    # Plain meter run is NOT review-flagged
    assert d["Review Flag"] is False


def test_price_meter_run_lact_routes_to_review():
    """LACT / custody-transfer must flag Review=True and skip auto-pricing.

    Curt's call: defer to Tier 3 (~10-20 such listings, $230k-$1.4M RCN
    range; complex packages that don't fit a generic meter-run bracket).
    """
    fx = json.loads(
        (Path(__file__).parent / "fixtures" / "meter_run_lact.json").read_text()
    )
    row = price_meter_run(fx)
    assert_row_satisfies_spec(row)
    d = row.to_dict()
    assert d["Family"] == "meter-run"
    assert d["Review Flag"] is True
    assert "LACT" in d["Review Reason"] or "custody" in d["Review Reason"].lower()
    assert d["Price Target LOW"] == 0
    assert d["Price Target MID"] == 0
    assert d["Price Target HIGH"] == 0
    assert "lact_custody_transfer" in d["Methodology Path"]


# ── Match-terms public surface ────────────────────────────────────

def test_match_terms_includes_canonical_phrases():
    terms = set(t.lower() for t in METER_RUN_MATCH_TERMS)
    assert "meter run" in terms
    assert "meter skid" in terms
    assert "metering skid" in terms
    assert "flow meter" in terms
    assert "flow run" in terms
