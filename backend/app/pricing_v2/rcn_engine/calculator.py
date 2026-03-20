"""RCN v2 master calculator — FMV = RCN_adj x AgeFactor x CondFactor x MktHeat x GeoFactor."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.pricing_v2.rcn_engine.condition import (
    get_condition_factor,
    infer_condition_from_hours,
    normalize_condition,
)
from app.pricing_v2.rcn_engine.confidence import ConfidenceBreakdown, calculate_confidence
from app.pricing_v2.rcn_engine.depreciation import (
    compute_effective_age,
    get_age_factor,
    get_curve_name,
)
from app.pricing_v2.rcn_engine.market_factors import (
    get_drive_factor,
    get_geography_factor,
    get_h2s_age_multiplier,
    get_market_heat_factor,
    get_material_factor,
    get_nace_premium,
)
from app.pricing_v2.rcn_engine.rcn_tables import (
    RCNInput,
    compute_base_rcn,
    compute_spec_modifiers_factor,
    normalize_category,
)

# ── POLICY CONSTANTS ──────────────────────────────────────────────────

DEFAULT_ASSUMED_AGE = 10
DEFAULT_DATA_AGE_WITH_COMPS = 30
DEFAULT_DATA_AGE_NO_COMPS = 365


@dataclass(frozen=True)
class RCNResult:
    rcn: float
    fair_market_value: float
    confidence: float
    factors_applied: dict[str, Any]
    depreciation_curve_used: str


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    numeric = _coerce_float(value)
    return int(numeric) if numeric is not None else None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    text = str(value).strip()
    return text or None


def _parse_input(specs: dict[str, Any]) -> RCNInput:
    """Parse a raw dict into a validated RCNInput."""
    payload = dict(specs)
    if "horsepower" not in payload and "hp" in payload:
        payload["horsepower"] = payload["hp"]
    if "is_nace_compliant" not in payload and "nace_compliant" in payload:
        payload["is_nace_compliant"] = payload["nace_compliant"]
    if "region" not in payload and "location" in payload:
        payload["region"] = payload["location"]

    return RCNInput(
        current_year=_coerce_int(payload.get("current_year")),
        year=_coerce_int(payload.get("year")),
        assumed_age_years=_coerce_int(payload.get("assumed_age_years")),
        hours=_coerce_float(payload.get("hours")),
        horsepower=_coerce_float(payload.get("horsepower")),
        weight_lbs=_coerce_float(payload.get("weight_lbs")),
        truck_class=_coerce_str(payload.get("truck_class")) or "class_8",
        equipment_type=_coerce_str(payload.get("equipment_type")) or "",
        condition=_coerce_str(payload.get("condition")),
        is_nace_compliant=_coerce_bool(payload.get("is_nace_compliant", False)),
        years_h2s_exposure=_coerce_float(payload.get("years_h2s_exposure")),
        wti_price=_coerce_float(payload.get("wti_price")),
        region=_coerce_str(payload.get("region")),
        location=_coerce_str(payload.get("location")),
        material=_coerce_str(payload.get("material")),
        drive_type=_coerce_str(payload.get("drive_type")),
        comparable_count=_coerce_int(payload.get("comparable_count")) or 0,
        comparable_cv=_coerce_float(payload.get("comparable_cv")),
        data_age_days=_coerce_int(payload.get("data_age_days")),
        spec_modifiers=payload.get("spec_modifiers"),
    )


def _resolve_condition_tier(specs: RCNInput, curve_name: str) -> tuple[str, bool, bool]:
    raw_condition = specs.condition
    hours = specs.hours
    has_hours = hours is not None and hours > 0
    if isinstance(raw_condition, str) and raw_condition.strip():
        return normalize_condition(raw_condition), True, has_hours
    inferred = infer_condition_from_hours(hours, curve_name)
    if inferred is not None:
        return inferred, True, has_hours
    return normalize_condition(None), False, has_hours


def calculate_rcn(category: str, specs: dict[str, Any]) -> RCNResult:
    """Calculate RCN-adjusted FMV using the v2 master formula."""
    validated = _parse_input(specs)
    category_key = normalize_category(category)
    curve_name = get_curve_name(category_key)

    current_year = validated.current_year or datetime.now(timezone.utc).year
    year = validated.year
    has_year = year is not None
    chronological_age = max(0, current_year - int(year)) if has_year else (validated.assumed_age_years or DEFAULT_ASSUMED_AGE)

    condition_tier, has_condition, has_hours = _resolve_condition_tier(validated, curve_name)
    effective_age = compute_effective_age(chronological_age, validated.hours, condition_tier, curve_name)

    is_nace = validated.is_nace_compliant
    h2s_mult = get_h2s_age_multiplier(validated.years_h2s_exposure or 0.0, is_nace)
    effective_age_sour = effective_age * h2s_mult

    age_factor = get_age_factor(effective_age_sour, category_key)
    condition_factor = get_condition_factor(condition_tier)
    base_rcn, rcn_quality, has_size = compute_base_rcn(category_key, validated)
    nace_prem = get_nace_premium(category_key, is_nace)
    mat_f = get_material_factor(validated.material)
    drv_f = get_drive_factor(validated.drive_type)
    spec_f = compute_spec_modifiers_factor(validated.spec_modifiers)

    rcn_adj = base_rcn * nace_prem * mat_f * drv_f * spec_f
    wti = validated.wti_price
    mkt_heat = get_market_heat_factor(wti, category_key) if wti is not None else 1.0
    geo_f = get_geography_factor(validated.region or validated.location)
    fmv = rcn_adj * age_factor * condition_factor * mkt_heat * geo_f

    comp_count = validated.comparable_count or 0
    data_age = validated.data_age_days
    if data_age is None:
        data_age = DEFAULT_DATA_AGE_WITH_COMPS if comp_count > 0 else DEFAULT_DATA_AGE_NO_COMPS

    conf = calculate_confidence(
        rcn_confidence=rcn_quality, comparable_count=comp_count,
        comparable_cv=validated.comparable_cv, has_year=has_year,
        has_condition=has_condition, has_hours=has_hours,
        has_size_param=has_size, data_age_days=data_age,
    )

    factors: dict[str, Any] = {
        "category_key": category_key, "chronological_age": chronological_age,
        "effective_age": round(effective_age, 4), "effective_age_sour": round(effective_age_sour, 4),
        "h2s_age_multiplier": round(h2s_mult, 4), "condition_tier": condition_tier,
        "rcn_base": round(base_rcn, 2), "nace_premium": nace_prem,
        "material_factor": mat_f, "drive_factor": drv_f,
        "spec_modifiers_factor": round(spec_f, 4), "rcn_adjusted": round(rcn_adj, 2),
        "age_factor": round(age_factor, 4), "condition_factor": round(condition_factor, 4),
        "market_heat": round(mkt_heat, 4), "geography_factor": round(geo_f, 4),
        "confidence_breakdown": {
            "rcn_source_score": conf.rcn_source_score, "data_volume_score": conf.data_volume_score,
            "data_freshness_score": conf.data_freshness_score, "specificity_score": conf.specificity_score,
            "variance_score": conf.variance_score, "composite": conf.composite,
        },
    }

    return RCNResult(
        rcn=round(rcn_adj, 2), fair_market_value=round(fmv, 2),
        confidence=round(conf.composite, 3), factors_applied=factors,
        depreciation_curve_used=curve_name,
    )
