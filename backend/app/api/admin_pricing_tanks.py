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
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException
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

# Tank-family category filter. Conservative — matches the dispatch scope.
_TANK_CATEGORY_PATTERNS = ("%tank%", "%storage%", "%bullet%")

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
async def run_tanks_bulk(authorization: str = Header(default="")):
    """Run the deterministic engine across every unpriced tank-family listing.

    Returns {run_id, total, succeeded, failed} on completion. Each priced row
    lands in `fuelled_valuations` with methodology='nova_v2/tank/seed-rcn' and
    review_status='draft'. Engine failures are recorded with status='failed'
    and an error_reason instead of aborting the run.
    """
    _require_admin(authorization)

    run_id = str(uuid.uuid4())
    total = 0
    succeeded = 0
    failed = 0

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
        result = await session.execute(
            text(
                """
                SELECT id, title, description, category, make, model, year,
                       horsepower, hours, weight_lbs, condition, location, source
                FROM listings
                WHERE fair_value IS NULL
                  AND (category ILIKE ANY (:patterns))
                """
            ),
            {"patterns": list(_TANK_CATEGORY_PATTERNS)},
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
        "methodology": METHODOLOGY_SLUG,
    }
