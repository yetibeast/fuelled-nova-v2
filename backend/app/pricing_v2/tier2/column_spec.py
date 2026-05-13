"""Tier 2 workbook column spec — LOCKED 2026-05-13.

Every family ruleset must emit a row that satisfies this schema.
The spec test (tests/pricing_v2/tier2/test_column_spec.py) is the
contract — do not bypass it.

Source: Mark Le Dain x Curt 2026-05-13 sync (Granola
3cd3ab18-a007-4b9c-b2c5-26fd03ff971a). Per-row transparency was
new requirement: methodology, confidence breakdown, L/M/H targets,
reasoning trail, factor weights — beyond the Tier 1 portfolio bands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ── REQUIRED COLUMNS (in order, frozen) ────────────────────────────
TIER2_COLUMNS: tuple[str, ...] = (
    # Identity
    "Listing ID",
    "Record ID",
    "Listing Name",
    "Category",
    "Family",            # NEW: which Tier 2 family (heater/treater/knockout-fwko/
                         #      knockout-gas/knockout-flare/dehydrator/ambiguous)
    "Supplier Company",
    "URL",
    # Inputs
    "Size / Basis",
    "Age Assumed (yr)",
    "Condition Assumed",
    # RCN
    "RCN New Low",
    "RCN New Mid",
    "RCN New High",
    "RCN Source",        # gold_table | fallback | sold_anchor
    # Methodology
    "Methodology Path",  # NEW: e.g. "dehydrator/teg/BTU-scaled"
    "Depreciation Curve",
    "Factor Service",
    "Factor Age",
    "Factor Condition",
    "Factor Combined",
    # Factor weights (constants — emitted per row for transparency)
    "Weight RCN Source",
    "Weight Data Volume",
    "Weight Freshness",
    "Weight Specificity",
    "Weight Variance",
    # Confidence breakdown (5 component scores + composite)
    "Conf RCN Source",
    "Conf Data Volume",
    "Conf Freshness",
    "Conf Specificity",
    "Conf Variance",
    "Conf Composite",
    "Conf Class",        # automated | hitl_review | manual
    # Price targets
    "Price Target LOW",  # risk-adjusted floor (walk-away)
    "Price Target MID",  # FMV center
    "Price Target HIGH", # ceiling (asking-anchor)
    # Comparables
    "Comparables Count",
    "Comparables Summary",
    # Reasoning trail
    "Reasoning Trail",   # NEW: multi-line factor-by-factor explanation
    "Review Flag",
    "Review Reason",     # NEW: non-empty when Review Flag is True
    "Hold From Publication",
    # Provenance
    "Sold Anchor Used",  # NEW: bool — true when sold-records corpus contributed
    "Sold Anchor Count", # NEW: number of sold records that influenced this row
)


# ── COLUMN TYPE CONTRACTS ──────────────────────────────────────────
COLUMN_TYPES: dict[str, type] = {
    "Listing ID": str, "Record ID": str, "Listing Name": str, "Category": str,
    "Family": str, "Supplier Company": str, "URL": str,
    "Size / Basis": str, "Age Assumed (yr)": (int, float), "Condition Assumed": str,
    "RCN New Low": (int, float), "RCN New Mid": (int, float), "RCN New High": (int, float),
    "RCN Source": str, "Methodology Path": str, "Depreciation Curve": str,
    "Factor Service": float, "Factor Age": float, "Factor Condition": float,
    "Factor Combined": float,
    "Weight RCN Source": float, "Weight Data Volume": float, "Weight Freshness": float,
    "Weight Specificity": float, "Weight Variance": float,
    "Conf RCN Source": float, "Conf Data Volume": float, "Conf Freshness": float,
    "Conf Specificity": float, "Conf Variance": float, "Conf Composite": float,
    "Conf Class": str,
    "Price Target LOW": (int, float), "Price Target MID": (int, float),
    "Price Target HIGH": (int, float),
    "Comparables Count": int, "Comparables Summary": str,
    "Reasoning Trail": str, "Review Flag": bool, "Review Reason": str,
    "Hold From Publication": bool,
    "Sold Anchor Used": bool, "Sold Anchor Count": int,
}


# ── VALID FAMILY VALUES ────────────────────────────────────────────
VALID_FAMILIES: frozenset[str] = frozenset({
    "dehydrator",
    "heater",
    "treater",
    "knockout-fwko",
    "knockout-gas",
    "knockout-flare",
    "knockout-ambiguous",  # disambiguation failed — flagged for review
})


VALID_CONF_CLASSES: frozenset[str] = frozenset({"automated", "hitl_review", "manual"})


@dataclass(frozen=True)
class Tier2Row:
    """A priced Tier 2 row. Use `.to_dict()` to render to workbook output."""
    data: dict

    def to_dict(self) -> dict:
        """Return ordered dict matching TIER2_COLUMNS order exactly."""
        return {col: self.data.get(col) for col in TIER2_COLUMNS}
