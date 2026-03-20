"""Base RCN reference tables and size-scaling logic.

Contains the category-specific base RCN values, HP/weight scaling,
category normalization, and spec modifier computation.

Source: V1 rcn_v2/calculator.py (table and lookup portions).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── POLICY CONSTANTS ──────────────────────────────────────────────────

DEFAULT_BASE_RCN = 100_000.0
DEFAULT_UNKNOWN_RCN_CONFIDENCE = 0.30
HP_SCALING_EXPONENT = 0.6
WEIGHT_SCALING_EXPONENT = 0.85
WEIGHT_SCALING_BASE_LBS = 10_000.0

# ── BASE RCN TABLES ──────────────────────────────────────────────────

ROTATING_BASE_RCN: dict[str, dict[str, dict[str, float]]] = {
    "compressor_package": {
        "reciprocating": {"base_rcn": 100_000, "base_hp": 100},
        "screw": {"base_rcn": 80_000, "base_hp": 100},
        "centrifugal": {"base_rcn": 160_000, "base_hp": 500},
    },
    "pump": {
        "centrifugal": {"base_rcn": 22_000, "base_hp": 50},
        "positive_displacement": {"base_rcn": 38_000, "base_hp": 50},
        "progressive_cavity": {"base_rcn": 18_000, "base_hp": 25},
    },
    "generator": {
        "diesel": {"base_rcn": 60_000, "base_hp": 100},
        "natural_gas": {"base_rcn": 75_000, "base_hp": 100},
        "dual_fuel": {"base_rcn": 85_000, "base_hp": 100},
    },
    "blower": {
        "rotary_lobe": {"base_rcn": 32_000, "base_hp": 50},
        "centrifugal": {"base_rcn": 48_000, "base_hp": 100},
    },
}

STATIC_BASE_RCN: dict[str, float] = {
    "separator": 130_000,
    "tank": 50_000,
    "treater": 200_000,
    "vessel": 110_000,
    "heater": 85_000,
}

HEAVY_EQUIP_BASE_RCN: dict[str, float] = {
    "loader": 250_000,
    "excavator": 300_000,
    "dozer": 350_000,
    "grader": 280_000,
    "backhoe": 120_000,
}

TRUCK_BASE_RCN: dict[str, float] = {
    "class_8": 280_000,
    "class_6_7": 150_000,
    "vocational": 200_000,
}

CATEGORY_BASE_MAP: dict[str, str] = {
    "compressors": "compressor_package",
    "compressor": "compressor_package",
    "compressor_package": "compressor_package",
    "separators": "separator",
    "separator": "separator",
    "vessel": "vessel",
    "tanks": "tank",
    "tank": "tank",
    "production": "treater",
    "treater": "treater",
    "heater": "heater",
    "pumps": "pump",
    "pump": "pump",
    "generators": "generator",
    "generator": "generator",
    "blower": "blower",
    "electrical": "e_house",
    "e_house": "e_house",
    "mcc": "e_house",
    "switchgear": "e_house",
    "vfd": "e_house",
    "loaders": "loader",
    "loader": "loader",
    "excavators": "excavator",
    "excavator": "excavator",
    "dozer": "dozer",
    "grader": "grader",
    "backhoe": "backhoe",
    "heavy_construction": "loader",
    "trucks": "truck",
    "truck": "truck",
    "trailers": "truck",
    "trailer": "truck",
}

DEFAULT_ROTATING_TYPE: dict[str, str] = {
    "compressor_package": "reciprocating",
    "pump": "centrifugal",
    "generator": "diesel",
    "blower": "rotary_lobe",
}


@dataclass
class RCNInput:
    """Validated calculator input. Plain dataclass — no Pydantic."""
    current_year: int | None = None
    year: int | None = None
    assumed_age_years: int | None = None
    hours: float | None = None
    horsepower: float | None = None
    weight_lbs: float | None = None
    truck_class: str = "class_8"
    equipment_type: str = ""
    condition: str | None = None
    is_nace_compliant: bool = False
    years_h2s_exposure: float | None = None
    wti_price: float | None = None
    region: str | None = None
    location: str | None = None
    material: str | None = None
    drive_type: str | None = None
    comparable_count: int = 0
    comparable_cv: float | None = None
    data_age_days: int | None = None
    spec_modifiers: dict[str, float] | list[float] | float | None = None


def normalize_category(category: str) -> str:
    """Normalize a category string to its base-table key."""
    normalized = category.strip().lower().replace("-", "_").replace(" ", "_")
    return CATEGORY_BASE_MAP.get(normalized, normalized)


def compute_spec_modifiers_factor(
    modifiers: dict[str, float] | list[float] | float | None,
) -> float:
    if modifiers is None:
        return 1.0
    factor = 1.0
    if isinstance(modifiers, dict):
        for value in modifiers.values():
            if value > 0:
                factor *= value
        return factor
    if isinstance(modifiers, list):
        for value in modifiers:
            if value > 0:
                factor *= value
        return factor
    return modifiers if modifiers > 0 else 1.0


def compute_base_rcn(
    category_key: str,
    specs: RCNInput,
) -> tuple[float, float, bool]:
    """Return (scaled_base_rcn, rcn_source_quality, has_size_param)."""
    horsepower = specs.horsepower
    weight_lbs = specs.weight_lbs
    truck_class = (specs.truck_class or "class_8").strip().lower().replace(" ", "_")
    equipment_type = (specs.equipment_type or "").strip().lower().replace(" ", "_")

    if category_key in ROTATING_BASE_RCN:
        type_map = ROTATING_BASE_RCN[category_key]
        resolved_type = equipment_type if equipment_type in type_map else DEFAULT_ROTATING_TYPE[category_key]
        params = type_map[resolved_type]
        base_rcn = float(params["base_rcn"])
        base_hp = float(params["base_hp"])
        if horsepower is not None and horsepower > 0:
            scaling = (horsepower / base_hp) ** HP_SCALING_EXPONENT
            quality = 0.80 if equipment_type in type_map else 0.70
            return base_rcn * scaling, quality, True
        quality = 0.60 if equipment_type in type_map else 0.50
        return base_rcn, quality, False

    if category_key in STATIC_BASE_RCN:
        base_rcn = float(STATIC_BASE_RCN[category_key])
        if weight_lbs is not None and weight_lbs > 0:
            scaling = (weight_lbs / WEIGHT_SCALING_BASE_LBS) ** WEIGHT_SCALING_EXPONENT
            return base_rcn * scaling, 0.70, True
        return base_rcn, 0.60, False

    if category_key in HEAVY_EQUIP_BASE_RCN:
        return float(HEAVY_EQUIP_BASE_RCN[category_key]), 0.70, False

    if category_key == "truck":
        return float(TRUCK_BASE_RCN.get(truck_class, TRUCK_BASE_RCN["class_8"])), 0.70, False

    return DEFAULT_BASE_RCN, DEFAULT_UNKNOWN_RCN_CONFIDENCE, False
