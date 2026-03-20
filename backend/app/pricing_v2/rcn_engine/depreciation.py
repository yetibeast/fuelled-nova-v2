"""Depreciation curves and effective-age logic.

Contains category-specific age curves with milestone-based linear interpolation,
effective age computation blending chronological age with hours and condition,
and curve-name resolution from category aliases.

Source: V1 rcn_v2/depreciation.py — all curves and formulas preserved exactly.
"""
from __future__ import annotations

from bisect import bisect_left

# ── POLICY CONSTANTS ──────────────────────────────────────────────────

# Category-specific age curves: (milestones, factors)
# Milestones = years, Factors = retention ratio at that age
AGE_CURVES: dict[str, tuple[list[int], list[float]]] = {
    "compressor": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35],
        [1.00, 0.94, 0.87, 0.79, 0.71, 0.59, 0.42, 0.28, 0.18, 0.14, 0.12],
    ),
    "separator": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35],
        [1.00, 0.95, 0.88, 0.81, 0.74, 0.63, 0.45, 0.30, 0.20, 0.14, 0.12],
    ),
    "tank": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30],
        [1.00, 0.93, 0.85, 0.76, 0.67, 0.54, 0.35, 0.20, 0.12, 0.10],
    ),
    "pump": (
        [0, 1, 3, 5, 7, 10, 15, 18, 22, 25],
        [1.00, 0.92, 0.83, 0.74, 0.65, 0.52, 0.32, 0.20, 0.12, 0.10],
    ),
    "generator": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30],
        [1.00, 0.93, 0.86, 0.78, 0.70, 0.58, 0.40, 0.25, 0.15, 0.12],
    ),
    "pump_jack": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35, 40],
        [1.00, 0.96, 0.91, 0.86, 0.80, 0.72, 0.57, 0.42, 0.30, 0.20, 0.14, 0.12],
    ),
    "electrical": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30],
        [1.00, 0.94, 0.87, 0.80, 0.72, 0.60, 0.40, 0.24, 0.14, 0.10],
    ),
    "treater": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30],
        [1.00, 0.93, 0.85, 0.76, 0.67, 0.54, 0.35, 0.20, 0.12, 0.10],
    ),
    "heavy_equip": (
        [0, 1, 3, 5, 7, 10, 15, 20, 25, 30],
        [1.00, 0.93, 0.86, 0.78, 0.70, 0.58, 0.40, 0.25, 0.17, 0.15],
    ),
    "truck": (
        [0, 1, 3, 5, 7, 10, 13, 15, 18, 20, 25],
        [1.00, 0.92, 0.83, 0.74, 0.65, 0.52, 0.38, 0.30, 0.22, 0.17, 0.17],
    ),
}

# Category name → depreciation curve key
CATEGORY_CURVE_MAP: dict[str, str] = {
    "compressor_package": "compressor",
    "compressor": "compressor",
    "compressors": "compressor",
    "separator": "separator",
    "separators": "separator",
    "vessel": "separator",
    "tank": "tank",
    "tanks": "tank",
    "treater": "treater",
    "treaters": "treater",
    "heater": "treater",
    "production": "treater",
    "pump": "pump",
    "pumps": "pump",
    "generator": "generator",
    "generators": "generator",
    "blower": "compressor",
    "pump_jack": "pump_jack",
    "beam_pump": "pump_jack",
    "e_house": "electrical",
    "electrical": "electrical",
    "mcc": "electrical",
    "switchgear": "electrical",
    "vfd": "electrical",
    "loader": "heavy_equip",
    "loaders": "heavy_equip",
    "excavator": "heavy_equip",
    "excavators": "heavy_equip",
    "dozer": "heavy_equip",
    "grader": "heavy_equip",
    "backhoe": "heavy_equip",
    "heavy_construction": "heavy_equip",
    "truck": "truck",
    "trucks": "truck",
    "trailer": "truck",
    "trailers": "truck",
}

DEFAULT_CURVE = "heavy_equip"

# Expected annual utilization hours by category curve
ANNUAL_HOURS: dict[str, int] = {
    "compressor": 6000,
    "separator": 8000,
    "tank": 8760,
    "pump": 5000,
    "generator": 4000,
    "pump_jack": 7000,
    "electrical": 8000,
    "treater": 7000,
    "heavy_equip": 1500,
    "truck": 2000,
}

# Condition adjustment factor for effective age when no hours available
CONDITION_AGE_FACTOR: dict[str, float] = {
    "EXCELLENT": 0.7,
    "VERY_GOOD": 0.85,
    "GOOD": 1.0,
    "FAIR": 1.2,
    "POOR": 1.4,
    "SCRAP": 2.0,
}


def get_curve_name(category: str | None) -> str:
    """Map category name to depreciation-curve key."""
    if not category:
        return DEFAULT_CURVE
    normalized = category.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in AGE_CURVES:
        return normalized
    if normalized in CATEGORY_CURVE_MAP:
        return CATEGORY_CURVE_MAP[normalized]
    return DEFAULT_CURVE


def compute_effective_age(
    chronological_age: int | float,
    hours: int | float | None,
    condition_tier: str | None,
    category_curve: str,
) -> float:
    """Compute effective age blending chronological age, hours, and condition."""
    chrono = max(0.0, float(chronological_age))
    curve = get_curve_name(category_curve)
    annual = float(ANNUAL_HOURS.get(curve, 4000))

    if hours is not None and float(hours) > 0:
        hour_implied_age = float(hours) / annual
        divergence = abs(hour_implied_age - chrono) / max(chrono, 1.0)
        if divergence > 0.5:
            effective = (0.7 * hour_implied_age) + (0.3 * chrono)
        else:
            effective = (0.5 * hour_implied_age) + (0.5 * chrono)
        return max(0.0, effective)

    if condition_tier and condition_tier in CONDITION_AGE_FACTOR:
        return max(0.0, chrono * CONDITION_AGE_FACTOR[condition_tier])

    return chrono


def _interp_linear(x: float, xp: list[int], fp: list[float]) -> float:
    """Linear interpolation for a monotonically increasing x-axis."""
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]

    idx = bisect_left(xp, x)
    x0, x1 = float(xp[idx - 1]), float(xp[idx])
    y0, y1 = float(fp[idx - 1]), float(fp[idx])
    if x1 == x0:
        return y0
    ratio = (x - x0) / (x1 - x0)
    return y0 + (ratio * (y1 - y0))


def get_age_factor(effective_age: int | float, category: str | None) -> float:
    """Get age factor using milestone-based curve interpolation."""
    curve_name = get_curve_name(category)
    milestones, factors = AGE_CURVES[curve_name]
    age = max(0.0, float(effective_age))
    if age > milestones[-1]:
        return float(factors[-1])
    return float(_interp_linear(age, milestones, factors))
