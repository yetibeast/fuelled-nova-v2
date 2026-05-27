"""Dehydrator family ruleset — Tier 2 vertical slice."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app.pricing_v2.tier2.dehydrator import (
    DEHYDRATOR_MATCH_TERMS,
    classify_dehydrator,
    dehydrator_rcn,
    dehydrator_service_factor,
    price_dehydrator,
)
from .test_column_spec import assert_row_satisfies_spec


def test_classify_dehydrator_teg():
    assert classify_dehydrator("TEG dehydrator 5 MMSCFD") == "teg"
    assert classify_dehydrator("triethylene glycol unit 10 MMSCFD") == "teg"


def test_classify_dehydrator_mole_sieve():
    assert classify_dehydrator("mole sieve dehydrator skid") == "mole_sieve"


def test_classify_dehydrator_generic():
    assert classify_dehydrator("dehydrator package") == "generic"


# ── Task 2.2: RCN scaling by MMSCFD throughput ──────────────────────
# Brackets re-calibrated 2026-05-26 to 2026 newbuild RCN. Anchor:
# 30" sour dehy = $600k-$1MM CAD (large bracket × 1.15× sour). Brackets
# back-solve with the steepened dehydrator depreciation curve below
# against HubSpot sold dehys (42" sour 15yr @ $200k → RCN ~$1MM ✓).
# See dehydrator.py for the full anchor + validation trail.

def test_dehydrator_rcn_small():
    rcn = dehydrator_rcn(variant="teg", mmscfd=2.0)
    assert rcn.low == 60_000 and rcn.mid == 100_000 and rcn.high == 130_000


def test_dehydrator_rcn_medium():
    rcn = dehydrator_rcn(variant="teg", mmscfd=15.0)
    assert rcn.low == 200_000 and rcn.mid == 300_000 and rcn.high == 400_000


def test_dehydrator_rcn_large():
    # 40 MMSCFD sits squarely in Large (25–50). The 30" sour anchor
    # (≈40 MMSCFD) maps here: Large × 1.15 = $598-1,001k matches the
    # $600k-$1MM Curt anchor.
    rcn = dehydrator_rcn(variant="teg", mmscfd=40.0)
    assert rcn.low == 520_000 and rcn.mid == 700_000 and rcn.high == 870_000


def test_dehydrator_rcn_mole_sieve_premium():
    teg = dehydrator_rcn(variant="teg", mmscfd=10.0)
    mole = dehydrator_rcn(variant="mole_sieve", mmscfd=10.0)
    assert mole.mid > teg.mid  # mole sieve carries premium


# ── Task 2.3: dedicated dehydrator depreciation curve ───────────────
# Steepened 2026-05-26 to match newbuild-RCN convention. 15yr retention
# ≈ 0.20 back-solved against 42" sour @ $200k sold price.

def test_dehydrator_age_factor_curve():
    # Curve flattened 2026-05-27 after reverse-pass against HubSpot
    # sold dehys ≥$25k. Old 15yr=0.20 was too steep — implied $3-4MM
    # RCN for 42-54" sour units, which is not real. New 15yr=0.40
    # produces $1.1-1.5MM implied RCN for those units, defensible.
    from backend.app.pricing_v2.rcn_engine.depreciation import get_age_factor
    assert get_age_factor(0, "dehydrator") == pytest.approx(1.00, rel=0.01)
    assert get_age_factor(10, "dehydrator") == pytest.approx(0.60, rel=0.05)
    assert get_age_factor(15, "dehydrator") == pytest.approx(0.40, rel=0.05)
    assert get_age_factor(20, "dehydrator") == pytest.approx(0.30, rel=0.10)


def test_dehydrator_rcn_mega_bracket():
    """≥50 MMSCFD (~48"+ diameter, major-plant scale) → Mega bracket."""
    rcn_75 = dehydrator_rcn(variant="teg", mmscfd=75.0)
    assert rcn_75.low == 1_000_000 and rcn_75.mid == 1_500_000 and rcn_75.high == 2_200_000


# ── Task 2.4: service factor (sweet vs sour) ──────────────────────

def test_dehydrator_service_factor_sweet():
    assert dehydrator_service_factor("sweet gas") == 1.00


def test_dehydrator_service_factor_sour():
    assert dehydrator_service_factor("sour gas H2S 2%") == 1.15


# ── Task 2.5: end-to-end pricing produces spec-compliant row ──────

def test_dehydrator_end_to_end_5mmscfd_teg():
    fx = json.loads(
        (Path(__file__).parent / "fixtures" / "dehydrator_5mmscfd_teg.json").read_text()
    )
    row = price_dehydrator(fx)
    # 1. Spec contract holds
    assert_row_satisfies_spec(row)
    # 2. Family routed correctly
    assert row.to_dict()["Family"] == "dehydrator"
    # 3. Methodology path traceable
    assert "teg" in row.to_dict()["Methodology Path"].lower()
    # 4. Reasoning trail is multi-line
    assert row.to_dict()["Reasoning Trail"].count("\n") >= 3
    # 5. Sold anchor not used (standalone run)
    assert row.to_dict()["Sold Anchor Used"] is False
    # 6. Confidence is composite-classified consistently
    composite = row.to_dict()["Conf Composite"]
    cls = row.to_dict()["Conf Class"]
    if composite >= 0.75:
        assert cls == "automated"
    elif composite >= 0.40:
        assert cls == "hitl_review"
    else:
        assert cls == "manual"
    # 7. Price targets bracket the FMV mid
    d = row.to_dict()
    fmv_mid = d["RCN New Mid"] * d["Factor Combined"]
    assert d["Price Target LOW"] < fmv_mid < d["Price Target HIGH"]
