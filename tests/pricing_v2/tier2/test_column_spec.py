"""Spec contract for Tier 2 row output.

Every family in Chunks 2-5 must produce rows that pass this test.
Adding a column? Add it to TIER2_COLUMNS in column_spec.py first,
then update this test. Never the other way around.
"""
from __future__ import annotations

import pytest

from backend.app.pricing_v2.tier2.column_spec import (
    COLUMN_TYPES,
    TIER2_COLUMNS,
    Tier2Row,
    VALID_CONF_CLASSES,
    VALID_FAMILIES,
)


def assert_row_satisfies_spec(row: Tier2Row) -> None:
    """Universal Tier 2 row validator. Called by every family test."""
    out = row.to_dict()

    # 1. All required columns present, in order
    assert tuple(out.keys()) == TIER2_COLUMNS, (
        f"Row keys do not match TIER2_COLUMNS order. "
        f"Got: {tuple(out.keys())}"
    )

    # 2. Type contract honored
    for col, expected in COLUMN_TYPES.items():
        val = out[col]
        if val is None:
            # None only allowed where Type is str (interpret as empty cell)
            assert expected is str, f"Column '{col}' is None but type is {expected}"
            continue
        if isinstance(expected, tuple):
            assert isinstance(val, expected), (
                f"Column '{col}' = {val!r} (type {type(val).__name__}), "
                f"expected one of {expected}"
            )
        else:
            assert isinstance(val, expected), (
                f"Column '{col}' = {val!r} (type {type(val).__name__}), "
                f"expected {expected.__name__}"
            )

    # 3. Family is a valid value
    assert out["Family"] in VALID_FAMILIES, (
        f"Family '{out['Family']}' not in VALID_FAMILIES"
    )

    # 4. Confidence class is valid
    assert out["Conf Class"] in VALID_CONF_CLASSES, (
        f"Conf Class '{out['Conf Class']}' not in VALID_CONF_CLASSES"
    )

    # 5. Price target ordering
    assert (
        out["Price Target LOW"]
        <= out["Price Target MID"]
        <= out["Price Target HIGH"]
    ), "Price targets out of order"

    # 6. RCN ordering
    assert out["RCN New Low"] <= out["RCN New Mid"] <= out["RCN New High"]

    # 7. Factor weights sum to 1.0 (these are constants — invariant)
    weight_sum = (
        out["Weight RCN Source"]
        + out["Weight Data Volume"]
        + out["Weight Freshness"]
        + out["Weight Specificity"]
        + out["Weight Variance"]
    )
    assert abs(weight_sum - 1.0) < 1e-6, f"Factor weights sum to {weight_sum}, not 1.0"

    # 8. Review flag must come with a reason when True
    if out["Review Flag"]:
        assert out["Review Reason"], "Review Flag True requires non-empty Review Reason"

    # 9. Sold anchor accounting consistent
    if out["Sold Anchor Used"]:
        assert out["Sold Anchor Count"] >= 1
    else:
        assert out["Sold Anchor Count"] == 0


def test_spec_columns_unique():
    """Sanity: no duplicate column names."""
    assert len(TIER2_COLUMNS) == len(set(TIER2_COLUMNS))


def test_spec_column_types_covers_all_columns():
    """Every column has a declared type."""
    missing = set(TIER2_COLUMNS) - set(COLUMN_TYPES.keys())
    assert not missing, f"COLUMN_TYPES missing entries for: {missing}"


def test_valid_families_includes_all_chunks():
    """Every family expected from Chunks 2-5 is declared."""
    required = {
        "dehydrator", "heater", "treater",
        "knockout-fwko", "knockout-gas", "knockout-flare",
        "knockout-ambiguous",
    }
    assert required.issubset(VALID_FAMILIES)


def test_minimal_synthetic_row_passes_validator():
    """The validator function itself runs cleanly on a hand-built valid row."""
    row = Tier2Row(data={
        # Identity
        "Listing ID": "L1", "Record ID": "R1", "Listing Name": "Test", "Category": "dehydrator",
        "Family": "dehydrator", "Supplier Company": "Test Co", "URL": "https://x",
        # Inputs
        "Size / Basis": "5 MMSCFD", "Age Assumed (yr)": 10, "Condition Assumed": "B",
        # RCN
        "RCN New Low": 100_000, "RCN New Mid": 150_000, "RCN New High": 200_000,
        "RCN Source": "fallback",
        # Methodology
        "Methodology Path": "dehydrator/teg/BTU-scaled",
        "Depreciation Curve": "dehydrator",
        "Factor Service": 1.0, "Factor Age": 0.6, "Factor Condition": 0.85,
        "Factor Combined": 0.51,
        # Weights
        "Weight RCN Source": 0.25, "Weight Data Volume": 0.25,
        "Weight Freshness": 0.10, "Weight Specificity": 0.25, "Weight Variance": 0.15,
        # Confidence
        "Conf RCN Source": 0.5, "Conf Data Volume": 0.4,
        "Conf Freshness": 0.6, "Conf Specificity": 0.7, "Conf Variance": 0.3,
        "Conf Composite": 0.5, "Conf Class": "hitl_review",
        # Price targets
        "Price Target LOW": 60_000, "Price Target MID": 76_500, "Price Target HIGH": 102_000,
        # Comps
        "Comparables Count": 0, "Comparables Summary": "no comps (standalone run)",
        # Reasoning
        "Reasoning Trail": "RCN: fallback dehydrator $100-200k.\nAge: 10yr -> 0.6.\nCondition: B -> 0.85.\nCombined: 0.51. FMV mid: $76.5k.",
        "Review Flag": False, "Review Reason": "",
        "Hold From Publication": False,
        # Provenance
        "Sold Anchor Used": False, "Sold Anchor Count": 0,
    })
    assert_row_satisfies_spec(row)
