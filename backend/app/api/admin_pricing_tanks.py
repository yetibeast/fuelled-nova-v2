"""POST /api/admin/pricing/tanks/run — Tier 2.5 tank bulk-runner.

Walks every listing where category matches a tank/storage/bullet pattern AND
fair_value IS NULL, extracts BBL from title/description, applies a
source-aware year default when year is missing, runs the deterministic
Tier 1 engine, and writes results to `fuelled_valuations` (review_status =
'draft') linked to a `pricing_runs` row.

Admin-only. Does NOT update `listings.fair_value` directly — that surfacing
step is a curator/reviewer responsibility (Phase B).

Year default policy (locked by Curt 2026-05-27):
  * source='fuelled'     → 2015
  * source='ironplanet'  → 2018
  * source='kijiji'      → 2010
  * all others           → 2015 (median fallback)

Methodology slug: 'nova_v2/tank/seed-rcn'.

LACT / custody-transfer / large metering skids are *deferred to Tier 3* and
are NOT in scope here — the tank category filter naturally excludes them.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import text

from app.api.admin import _require_admin
from app.db.session import get_session
from app.pricing_v2.equipment.parsing import extract_tank_volume_bbl
from app.pricing_v2.rcn_engine.calculator import calculate_rcn

router = APIRouter()
_log = logging.getLogger(__name__)


# ── POLICY ────────────────────────────────────────────────────────────

METHODOLOGY_SLUG = "nova_v2/tank/seed-rcn"
METHODOLOGY_VERSION = "nova_v2"

# Tank-family category filter. Excludes `tanker-trailers` (transport, not
# production tanks — Tier 3 deferral per scoping doc).
_TANK_CATEGORY_PATTERNS = ("%tank%", "%storage%", "%bullet%")
_TANK_CATEGORY_EXCLUDES = ("%tanker-trailer%", "%tanker_trailer%")

# Listings that match the category pattern but clearly aren't production
# pressure vessels — portable poly fuel skids, plastic sewer / water /
# camp tanks, trailer-mounted asphalt units, etc. Caught from the 2026-05-27
# limit=10 graduated run.
_NON_PRODUCTION_TITLE_PATTERN = re.compile(
    r"\b(poly|plastic|sewer|water|water\s+canon|portable|tow\s+behind|trailer\s+mounted|"
    r"camp|overhead|fuel\s+tank|diesel\s+tank|chemical|wash\s+tank|septic)\b",
    re.IGNORECASE,
)

# Production tanks below this size are typically skid / pickup-truck mounted
# and not in the pressure-vessel-class the bracket ladder is calibrated for.
_MIN_BBL_FOR_BULK_PRICING = 50

# Source-aware year defaults (locked policy).
_SOURCE_YEAR_DEFAULTS: dict[str, int] = {
    "fuelled": 2015,
    "ironplanet": 2018,
    "kijiji": 2010,
}
_DEFAULT_YEAR_FALLBACK = 2015


def _default_year_for_source(source: str | None) -> int:
    if not source:
        return _DEFAULT_YEAR_FALLBACK
    return _SOURCE_YEAR_DEFAULTS.get(source.strip().lower(), _DEFAULT_YEAR_FALLBACK)


def _scope_filter(row: dict[str, Any]) -> str | None:
    """Return a skip reason if the row is out of scope, else None.

    The tank bracket ladder is calibrated for production-scale steel
    pressure vessels (100-750 BBL seed entries). Listings that are
    plastic/poly skids, transport trailers, or sub-50-BBL portable
    units get nonsense prices from the $/BBL extrapolation. Skip them
    explicitly so the run's `skipped` counter surfaces the exclusion
    instead of producing bad valuations.
    """
    title = (row.get("title") or "") + " " + (row.get("description") or "")
    if _NON_PRODUCTION_TITLE_PATTERN.search(title):
        return "non-production tank (poly / plastic / sewer / portable / trailer-mounted)"

    # Volume gate: only price rows with extracted BBL >= 50.
    # Imported lazily inside the function to keep top-level imports clean.
    from app.pricing_v2.equipment.parsing import extract_tank_volume_bbl
    bbl = extract_tank_volume_bbl(row.get("title") or "") or extract_tank_volume_bbl(row.get("description") or "")
    if bbl is None:
        return "no extractable volume — needs manual review"
    if bbl < _MIN_BBL_FOR_BULK_PRICING:
        return f"sub-{_MIN_BBL_FOR_BULK_PRICING}-BBL ({bbl:.0f}) — skid/portable class, not pressure vessel"
    return None


def _price_one_tank(row: dict[str, Any]) -> dict[str, Any]:
    """Price a single tank listing. Returns a dict with engine output + status.

    Pure function — no DB writes. Caller handles persistence.
    """
    title = row.get("title") or ""
    description = row.get("description") or ""
    volume_bbl = extract_tank_volume_bbl(title) or extract_tank_volume_bbl(description)

    year = row.get("year")
    if year is None:
        year = _default_year_for_source(row.get("source"))

    specs: dict[str, Any] = {
        "year": year,
        "volume_bbl": volume_bbl,
        "horsepower": row.get("horsepower"),
        "weight_lbs": row.get("weight_lbs"),
        "hours": row.get("hours"),
        "condition": row.get("condition"),
        "location": row.get("location"),
    }
    result = calculate_rcn(row.get("category") or "tank", specs)
    fmv_mid = result.fair_market_value
    fmv_low = round(fmv_mid * 0.85, 2)
    fmv_high = round(fmv_mid * 1.15, 2)
    return {
        "fmv_low": fmv_low,
        "fmv_mid": fmv_mid,
        "fmv_high": fmv_high,
        "confidence_composite": result.confidence,
        "volume_bbl": volume_bbl,
        "year_used": year,
    }


def _confidence_class(composite: float) -> str:
    if composite >= 0.70:
        return "HIGH"
    if composite >= 0.50:
        return "MEDIUM"
    return "LOW"


@router.post("/admin/pricing/tanks/run")
async def run_tanks_bulk(
    authorization: str = Header(default=""),
    limit: int = Query(0, ge=0, le=10000, description="0 = no cap (full run); N > 0 caps the candidate set for staged rollouts."),
):
    """Run the deterministic engine across unpriced tank-family listings.

    Returns {run_id, total, succeeded, failed} on completion. Each priced row
    lands in `fuelled_valuations` with methodology='nova_v2/tank/seed-rcn' and
    review_status='draft'. Engine failures are recorded with status='failed'
    and an error_reason instead of aborting the run.

    `limit` defaults to 0 (no cap). Pass `?limit=10` to run a small
    graduated batch before turning loose on the full backlog. Useful for
    first-time prod invocations; the run_id still tracks the partial run
    so it can be inspected end-to-end.
    """
    _require_admin(authorization)

    run_id = str(uuid.uuid4())
    total = 0
    succeeded = 0
    failed = 0
    skipped = 0
    skip_reasons: dict[str, int] = {}

    async with get_session() as session:
        # Create the pricing_runs row up front so failures still leave a trail.
        await session.execute(
            text(
                "INSERT INTO pricing_runs (run_id, status, methodology_version, notes) "
                "VALUES (:run_id, 'running', :version, :notes)"
            ),
            {
                "run_id": run_id,
                "version": METHODOLOGY_VERSION,
                "notes": "tanks bulk runner (Tier 2.5)",
            },
        )

        # Pull the candidate set. Use ILIKE ANY for the category filter.
        # When limit > 0, cap the row count for graduated rollouts; ORDER BY
        # id keeps the slice stable across calls so an aborted partial run
        # can be re-issued without re-pricing the same head.
        limit_clause = " ORDER BY id LIMIT :lim" if limit > 0 else ""
        params: dict[str, Any] = {
            "patterns": list(_TANK_CATEGORY_PATTERNS),
            "excludes": list(_TANK_CATEGORY_EXCLUDES),
        }
        if limit > 0:
            params["lim"] = limit
        result = await session.execute(
            text(
                f"""
                SELECT id, title, description, category, make, model, year,
                       horsepower, hours, weight_lbs, condition, location, source
                FROM listings
                WHERE fair_value IS NULL
                  AND (category ILIKE ANY (:patterns))
                  AND NOT (category ILIKE ANY (:excludes))
                {limit_clause}
                """
            ),
            params,
        )
        rows = result.fetchall()
        total = len(rows)

        for r in rows:
            row_dict = {
                "id": r[0], "title": r[1], "description": r[2], "category": r[3],
                "make": r[4], "model": r[5], "year": r[6],
                "horsepower": r[7], "hours": r[8], "weight_lbs": r[9],
                "condition": r[10], "location": r[11], "source": r[12],
            }

            # Scope filter: skip non-production / sub-50-BBL rows up front so
            # they don't produce nonsense bracketed prices. Skip != failure;
            # skipped rows are explicitly out of scope and counted separately.
            skip_reason = _scope_filter(row_dict)
            if skip_reason is not None:
                skipped += 1
                skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                continue

            valuation_id = str(uuid.uuid4())
            try:
                priced = _price_one_tank(row_dict)
                await session.execute(
                    text(
                        """
                        INSERT INTO fuelled_valuations
                            (id, listing_id, fmv_low, fmv_mid, fmv_high,
                             confidence, status, tier, data_completeness,
                             tools_used, trace_id, methodology, review_status, run_id)
                        VALUES
                            (:id, :lid, :fmv_low, :fmv_mid, :fmv_high,
                             :conf, 'success', 1, 0,
                             'rcn_engine', :trace, :methodology, 'draft', :run_id)
                        """
                    ),
                    {
                        "id": valuation_id,
                        "lid": row_dict["id"],
                        "fmv_low": priced["fmv_low"],
                        "fmv_mid": priced["fmv_mid"],
                        "fmv_high": priced["fmv_high"],
                        "conf": _confidence_class(priced["confidence_composite"]),
                        "trace": run_id,
                        "methodology": METHODOLOGY_SLUG,
                        "run_id": run_id,
                    },
                )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 — record failure, continue run
                failed += 1
                _log.warning("tank pricing failed for listing %s: %r", row_dict.get("id"), exc)
                try:
                    await session.execute(
                        text(
                            """
                            INSERT INTO fuelled_valuations
                                (id, listing_id, status, error_reason,
                                 tier, data_completeness, methodology,
                                 review_status, run_id)
                            VALUES
                                (:id, :lid, 'failed', :err,
                                 1, 0, :methodology, 'draft', :run_id)
                            """
                        ),
                        {
                            "id": valuation_id,
                            "lid": row_dict["id"],
                            "err": repr(exc)[:500],
                            "methodology": METHODOLOGY_SLUG,
                            "run_id": run_id,
                        },
                    )
                except Exception:
                    pass  # Best-effort audit; never let bookkeeping abort the loop.

        # Finalize the pricing_runs row.
        status = "succeeded" if failed == 0 else ("partial" if succeeded > 0 else "failed")
        await session.execute(
            text(
                """
                UPDATE pricing_runs
                SET finished_at = NOW(),
                    status = :status,
                    listings_total = :total,
                    listings_succeeded = :succ,
                    listings_failed = :failed
                WHERE run_id = :run_id
                """
            ),
            {
                "run_id": run_id,
                "status": status,
                "total": total,
                "succ": succeeded,
                "failed": failed,
            },
        )
        await session.commit()

    return {
        "run_id": run_id,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "skip_reasons": skip_reasons,
        "methodology": METHODOLOGY_SLUG,
    }
