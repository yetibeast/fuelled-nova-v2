"""POST /api/v2/price — Nova Core deterministic pricing capability.

Phase A2 scope: deterministic Tier 1 path only.
  * Tier 1 hit: compressor / pump / separator / tank / treater / vessel / heater
    / generator / blower with sufficient structured fields → call rcn_engine,
    return {fmv_low, fmv_mid, fmv_high, methodology, confidence, ...}.
  * Tier 1 miss: any other family → return {status: "unsupported_family",
    methodology: "nova_v2/unsupported"} for the caller to route elsewhere.

Out of scope (next dispatch):
  * LLM identity resolution for unstructured listing titles.
  * Reasoning trail composition (deterministic template only for now).
  * Comparables pull from listings + pricing_evidence_intake.
  * Tier 2 family rulesets (parallel agent owns those).
  * Writes to fuelled_valuations (read-only endpoint until A3).

Architecture spec: docs/superpowers/specs/2026-05-20-nova-engine-architecture-spec.md
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.api.admin import _require_auth
from app.db.session import get_session
from app.pricing_v2.rcn_engine.calculator import calculate_rcn
from app.pricing_v2.rcn_engine.rcn_tables import (
    CATEGORY_BASE_MAP,
    HEAVY_EQUIP_BASE_RCN,
    ROTATING_BASE_RCN,
    STATIC_BASE_RCN,
    normalize_category,
)

router = APIRouter(tags=["v2_price"])

ENGINE_VERSION = "nova_v2"
DEFAULT_CURRENCY = "CAD"

# Categories the deterministic Tier 1 engine has a base RCN for.
# Anything outside this set falls through to unsupported_family.
_TIER1_SUPPORTED_CATEGORIES: set[str] = (
    set(ROTATING_BASE_RCN.keys()) | set(STATIC_BASE_RCN.keys()) | set(HEAVY_EQUIP_BASE_RCN.keys()) | {"truck"}
)


class AdHocListing(BaseModel):
    """Off-platform listing data — caller supplies what they know."""
    title: Optional[str] = None
    category: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    horsepower: Optional[float] = None
    weight_lbs: Optional[float] = None
    hours: Optional[float] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    asking_price: Optional[float] = None
    currency: Optional[str] = None
    is_nace_compliant: Optional[bool] = None
    years_h2s_exposure: Optional[float] = None
    material: Optional[str] = None
    drive_type: Optional[str] = None


class V2PriceRequest(BaseModel):
    """Caller supplies one of: listing_id (engine pulls from DB) or ad_hoc (caller-supplied)."""
    listing_id: Optional[str] = None
    ad_hoc: Optional[AdHocListing] = None


def _confidence_class(composite: float) -> str:
    if composite >= 0.70:
        return "HIGH"
    if composite >= 0.50:
        return "MEDIUM"
    return "LOW"


def _build_methodology(category_key: str, rcn_source: str) -> str:
    family = category_key or "unknown"
    return f"{ENGINE_VERSION}/{family}/{rcn_source}"


def _unsupported_response(trace_id: str, category: str | None, reason: str) -> dict:
    return {
        "status": "unsupported_family",
        "methodology": f"{ENGINE_VERSION}/unsupported",
        "fmv_low": None,
        "fmv_mid": None,
        "fmv_high": None,
        "currency": DEFAULT_CURRENCY,
        "confidence": "LOW",
        "tier": None,
        "tools_used": [],
        "reasoning_trail": reason,
        "trace_id": trace_id,
        "engine_version": ENGINE_VERSION,
        "category_seen": category,
    }


def _specs_from_listing(data: dict[str, Any]) -> dict[str, Any]:
    """Map listing/ad_hoc dict to rcn_engine RCNInput kwargs."""
    return {
        "year": data.get("year"),
        "hours": data.get("hours"),
        "horsepower": data.get("horsepower"),
        "weight_lbs": data.get("weight_lbs"),
        "condition": data.get("condition"),
        "is_nace_compliant": data.get("is_nace_compliant") or False,
        "years_h2s_exposure": data.get("years_h2s_exposure"),
        "location": data.get("location"),
        "material": data.get("material"),
        "drive_type": data.get("drive_type"),
    }


async def _load_listing(listing_id: str) -> dict[str, Any] | None:
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT id, title, category, make, model, year, horsepower, hours, "
                "condition, location, asking_price "
                "FROM listings WHERE id = :lid"
            ),
            {"lid": listing_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "title": row[1],
            "category": row[2],
            "make": row[3],
            "model": row[4],
            "year": row[5],
            "horsepower": row[6],
            "hours": row[7],
            "condition": row[8],
            "location": row[9],
            "asking_price": row[10],
        }


def _price_deterministic(listing_data: dict[str, Any], trace_id: str) -> dict[str, Any]:
    """Run the deterministic Tier 1 path. Caller has already verified the family is supported."""
    category_raw = listing_data.get("category") or ""
    category_key = normalize_category(category_raw)

    specs = _specs_from_listing(listing_data)
    result = calculate_rcn(category_raw, specs)
    fa = result.factors_applied
    fmv_mid = result.fair_market_value
    # ±15% band — matches existing tools.calculate_fmv convention.
    fmv_low = round(fmv_mid * 0.85, 2)
    fmv_high = round(fmv_mid * 1.15, 2)

    composite = fa.get("confidence_breakdown", {}).get("composite", 0.0)
    conf_class = _confidence_class(composite)

    # rcn_source: gold-table once the rcn_price_references join wires in; today
    # we're computing off the in-code base-RCN tables.
    methodology = _build_methodology(category_key, rcn_source="rcn_table")

    reasoning_trail = (
        f"Category {category_raw!r} normalized to {category_key!r}.\n"
        f"Base RCN (engine table) ${fa['rcn_base']:,.0f}; adjusted to ${fa['rcn_adjusted']:,.0f}.\n"
        f"Effective age {fa['effective_age']:.1f} yr, condition {fa['condition_tier']}.\n"
        f"Factors: age={fa['age_factor']:.3f}, cond={fa['condition_factor']:.3f}, "
        f"market_heat={fa['market_heat']:.3f}, geo={fa['geography_factor']:.3f}.\n"
        f"Curve: {result.depreciation_curve_used}. Confidence composite: {composite:.2f}."
    )

    return {
        "status": "success",
        "methodology": methodology,
        "fmv_low": fmv_low,
        "fmv_mid": fmv_mid,
        "fmv_high": fmv_high,
        "currency": DEFAULT_CURRENCY,
        "confidence": conf_class,
        "confidence_score": round(composite, 3),
        "tier": 1,
        "tools_used": ["rcn_engine"],
        "reasoning_trail": reasoning_trail,
        "factors": {
            "age": fa["age_factor"],
            "condition": fa["condition_factor"],
            "market_heat": fa["market_heat"],
            "geography": fa["geography_factor"],
        },
        "rcn_new": {
            "low": round(fa["rcn_adjusted"] * 0.85, 2),
            "mid": round(fa["rcn_adjusted"], 2),
            "high": round(fa["rcn_adjusted"] * 1.15, 2),
        },
        "depreciation_curve": result.depreciation_curve_used,
        "trace_id": trace_id,
        "engine_version": ENGINE_VERSION,
        "category_key": category_key,
    }


@router.post("/v2/price")
async def post_v2_price(
    payload: V2PriceRequest,
    authorization: str = Header(default=""),
):
    _require_auth(authorization)

    if not payload.listing_id and not payload.ad_hoc:
        raise HTTPException(status_code=400, detail="Provide either 'listing_id' or 'ad_hoc'")

    trace_id = f"v2-{uuid.uuid4().hex[:12]}"

    # Resolve input to a unified listing dict
    if payload.listing_id:
        listing_data = await _load_listing(payload.listing_id)
        if not listing_data:
            raise HTTPException(status_code=404, detail=f"listing {payload.listing_id} not found")
    else:
        listing_data = payload.ad_hoc.model_dump()

    category = listing_data.get("category") or ""
    category_key = normalize_category(category)

    if category_key not in _TIER1_SUPPORTED_CATEGORIES:
        return _unsupported_response(
            trace_id=trace_id,
            category=category,
            reason=(
                f"Category {category!r} (normalized: {category_key!r}) has no Tier 1 ruleset. "
                "Tier 2 family rulesets land in a follow-up dispatch."
            ),
        )

    try:
        return _price_deterministic(listing_data, trace_id=trace_id)
    except Exception as exc:  # noqa: BLE001 — engine is wrapped so callers get structured error
        raise HTTPException(
            status_code=500,
            detail={
                "code": "internal_error",
                "message": f"deterministic engine failed: {exc!r}",
                "trace_id": trace_id,
            },
        ) from exc
