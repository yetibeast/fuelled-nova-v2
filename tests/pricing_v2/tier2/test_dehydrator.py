"""Dehydrator family ruleset — Tier 2 vertical slice."""
from __future__ import annotations

import pytest

from backend.app.pricing_v2.tier2.dehydrator import (
    DEHYDRATOR_MATCH_TERMS,
    classify_dehydrator,
    price_dehydrator,
)
from tests.pricing_v2.tier2.test_column_spec import assert_row_satisfies_spec


def test_classify_dehydrator_teg():
    assert classify_dehydrator("TEG dehydrator 5 MMSCFD") == "teg"
    assert classify_dehydrator("triethylene glycol unit 10 MMSCFD") == "teg"


def test_classify_dehydrator_mole_sieve():
    assert classify_dehydrator("mole sieve dehydrator skid") == "mole_sieve"


def test_classify_dehydrator_generic():
    assert classify_dehydrator("dehydrator package") == "generic"
