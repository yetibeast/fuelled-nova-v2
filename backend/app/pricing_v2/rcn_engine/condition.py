"""Condition normalization and condition-factor logic.

Maps raw marketplace condition labels to standardized tiers and returns
the corresponding depreciation multiplier.

Source: V1 rcn_v2/condition.py — all rule tables preserved exactly.
"""
from __future__ import annotations

# ── POLICY CONSTANTS ──────────────────────────────────────────────────
# Condition tier → depreciation multiplier
CONDITION_FACTORS: dict[str, float] = {
    "EXCELLENT": 0.95,
    "VERY_GOOD": 0.85,
    "GOOD": 0.75,
    "FAIR": 0.60,
    "POOR": 0.40,
    "SCRAP": 0.12,
}

DEFAULT_CONDITION = "GOOD"

# Marketplace status strings that are NOT condition labels
NON_CONDITION_VALUES = {"active", "sold", "expired", "delisted", "pending"}

# Raw string → tier mapping (lowercase keys)
CONDITION_STRING_MAP: dict[str, str] = {
    "new": "EXCELLENT",
    "newcondition": "EXCELLENT",
    "new/unused": "EXCELLENT",
    "excellent": "EXCELLENT",
    "very good": "VERY_GOOD",
    "very_good": "VERY_GOOD",
    "good": "GOOD",
    "rebuilt": "GOOD",
    "refurbished": "GOOD",
    "reconditioned": "GOOD",
    "used": "GOOD",
    "usedcondition": "GOOD",
    "used/see description": "GOOD",
    "used-b": "FAIR",
    "fair": "FAIR",
    "used-c": "POOR",
    "poor": "POOR",
    "salvage": "SCRAP",
    "scrap": "SCRAP",
    "parts": "SCRAP",
    "parts only": "SCRAP",
    "for parts": "SCRAP",
    "inoperable": "SCRAP",
    "not running": "POOR",
    "as-is": "FAIR",
    "as is": "FAIR",
}

# Category-specific hours → condition thresholds
HOURS_CONDITION_THRESHOLDS: dict[str, dict[str, int]] = {
    "compressor": {
        "EXCELLENT": 8_000,
        "VERY_GOOD": 20_000,
        "GOOD": 40_000,
        "FAIR": 60_000,
    },
    "separator": {
        "EXCELLENT": 20_000,
        "VERY_GOOD": 40_000,
        "GOOD": 60_000,
        "FAIR": 80_000,
    },
    "pump": {
        "EXCELLENT": 8_000,
        "VERY_GOOD": 20_000,
        "GOOD": 35_000,
        "FAIR": 50_000,
    },
    "generator": {
        "EXCELLENT": 5_000,
        "VERY_GOOD": 15_000,
        "GOOD": 30_000,
        "FAIR": 50_000,
    },
    "heavy_equip": {
        "EXCELLENT": 2_000,
        "VERY_GOOD": 5_000,
        "GOOD": 10_000,
        "FAIR": 18_000,
    },
    "truck": {
        "EXCELLENT": 3_000,
        "VERY_GOOD": 8_000,
        "GOOD": 15_000,
        "FAIR": 25_000,
    },
}


def normalize_condition(raw: str | None) -> str:
    """Normalize raw marketplace condition labels to a v2 condition tier."""
    if raw is None or not isinstance(raw, str):
        return DEFAULT_CONDITION

    normalized = " ".join(raw.lower().strip().split())
    if normalized in NON_CONDITION_VALUES:
        return DEFAULT_CONDITION
    if normalized in CONDITION_STRING_MAP:
        return CONDITION_STRING_MAP[normalized]

    normalized_underscore = normalized.replace(" ", "_")
    if normalized_underscore in CONDITION_STRING_MAP:
        return CONDITION_STRING_MAP[normalized_underscore]

    return DEFAULT_CONDITION


def infer_condition_from_hours(
    hours: int | float | None,
    category_curve: str,
) -> str | None:
    """Infer condition tier from operating hours with category-specific thresholds.

    Returns None for hours <= 0 (treat as "no data") to stay consistent with
    compute_effective_age(), which also treats 0 hours as missing.
    """
    if hours is None:
        return None
    numeric_hours = float(hours)
    if numeric_hours <= 0:
        return None

    thresholds = HOURS_CONDITION_THRESHOLDS.get(
        category_curve, HOURS_CONDITION_THRESHOLDS["compressor"]
    )
    for tier in ("EXCELLENT", "VERY_GOOD", "GOOD", "FAIR"):
        if numeric_hours < thresholds[tier]:
            return tier
    return "POOR"


def get_condition_factor(condition_tier: str | None) -> float:
    """Return multiplier for a normalized condition tier."""
    if condition_tier is None:
        return CONDITION_FACTORS[DEFAULT_CONDITION]
    return CONDITION_FACTORS.get(condition_tier, CONDITION_FACTORS[DEFAULT_CONDITION])
