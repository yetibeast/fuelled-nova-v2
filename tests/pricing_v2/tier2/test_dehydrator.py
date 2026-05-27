"""Dehydrator family ruleset — Tier 2 vertical slice."""
from __future__ import annotations

import pytest

from backend.app.pricing_v2.tier2.dehydrator import (
    DEHYDRATOR_MATCH_TERMS,
    classify_dehydrator,
    dehydrator_rcn,
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
# NOTE: bracket values are placeholders — Curt confirms against
# seeds/rcn_price_reference_seed_v2.xlsx before Chunk 2 closes.

def test_dehydrator_rcn_small():
    rcn = dehydrator_rcn(variant="teg", mmscfd=2.0)
    assert rcn.low == 50_000 and rcn.mid == 100_000 and rcn.high == 150_000


def test_dehydrator_rcn_medium():
    rcn = dehydrator_rcn(variant="teg", mmscfd=15.0)
    assert rcn.low == 150_000 and rcn.mid == 275_000 and rcn.high == 400_000


def test_dehydrator_rcn_large():
    rcn = dehydrator_rcn(variant="teg", mmscfd=50.0)
    assert rcn.low == 400_000 and rcn.mid == 700_000 and rcn.high == 1_000_000


def test_dehydrator_rcn_mole_sieve_premium():
    teg = dehydrator_rcn(variant="teg", mmscfd=10.0)
    mole = dehydrator_rcn(variant="mole_sieve", mmscfd=10.0)
    assert mole.mid > teg.mid  # mole sieve carries premium


# ── Task 2.3: dedicated dehydrator depreciation curve ───────────────
# Existing API is get_age_factor(effective_age, category); plan
# snippet's age_factor() name does not exist in the engine. Adapted
# to call the real primitive — keeps rcn_engine surface unchanged.

def test_dehydrator_age_factor_curve():
    from backend.app.pricing_v2.rcn_engine.depreciation import get_age_factor
    assert get_age_factor(0, "dehydrator") == pytest.approx(1.00, rel=0.01)
    assert get_age_factor(10, "dehydrator") == pytest.approx(0.60, rel=0.05)
    assert get_age_factor(20, "dehydrator") == pytest.approx(0.35, rel=0.05)
