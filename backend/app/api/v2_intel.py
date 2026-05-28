"""GET /api/v2/intel/status, GET /api/v2/intel/queue.

Read-only admin endpoints powering the Marketing Agent UI's recurring-
enrichment dashboard. Status shows queue summary + recent runs + totals.
Queue returns the pending list (paginated).

Spec: docs/superpowers/specs/2026-05-20-nova-engine-architecture-spec.md
      §§ "Contracts — Intel capability APIs", "Recurring pipeline"

Future endpoints (next dispatch):
  POST /api/v2/intel/sellers/enrich         — single-seller research
  POST /api/v2/intel/sellers/enrich-batch   — UI-triggered batch
  GET  /api/v2/intel/sellers/{name}         — drill-down
  POST /api/v2/intel/buyers/research        — buy-side research
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, Query
from sqlalchemy import text

from app.api.admin import _require_admin
from app.db.session import get_session

router = APIRouter(tags=["v2_intel"])
_log = logging.getLogger(__name__)


_QUEUE_TOP_SQL = text(
    "SELECT seller_name, source, listing_volume, last_seen, "
    "       last_researched_at, attempts, freshness "
    "FROM enrichment_queue "
    "LIMIT :lim"
)

_QUEUE_PAGED_SQL = text(
    "SELECT seller_name, source, listing_volume, last_seen, "
    "       last_researched_at, attempts, freshness "
    "FROM enrichment_queue "
    "LIMIT :lim OFFSET :off"
)

_RECENT_RUNS_SQL = text(
    "SELECT run_id, started_at, finished_at, trigger, provider_chain, "
    "       sellers_total, sellers_succeeded, sellers_failed, "
    "       contacts_added, cost_usd, notes "
    "FROM enrichment_runs "
    "ORDER BY started_at DESC "
    "LIMIT :lim"
)


def _q_row(row: Any) -> dict:
    """Normalize a row object (dict-backed or attribute-backed) to dict."""
    if hasattr(row, "_data") and isinstance(row._data, dict):
        return dict(row._data)
    if isinstance(row, dict):
        return dict(row)
    # Tuple-style row — fall back to known column order.
    return {
        "seller_name": row[0],
        "source": row[1],
        "listing_volume": row[2],
        "last_seen": row[3],
        "last_researched_at": row[4],
        "attempts": row[5],
        "freshness": row[6],
    }


def _iso(val: Any) -> Optional[str]:
    if val is None:
        return None
    iso = getattr(val, "isoformat", None)
    return iso() if iso else str(val)


@router.get("/v2/intel/status")
async def intel_status(authorization: str | None = Header(default=None)):
    """Summary of pipeline health: queue stats + recent runs + totals."""
    _require_admin(authorization)

    async with get_session() as session:
        # Pull the full queue once — view is cheap.
        res = await session.execute(_QUEUE_TOP_SQL, {"lim": 10000})
        queue_rows = [_q_row(r) for r in res.fetchall()]

        # Recent runs (last 10).
        res2 = await session.execute(_RECENT_RUNS_SQL, {"lim": 10})
        run_rows = [_q_row_run(r) for r in res2.fetchall()]

        # Totals.
        contacts_res = await session.execute(
            text("SELECT COUNT(*) FROM seller_contact_enrichment "
                 "WHERE contact_email IS NOT NULL")
        )
        contact_count_row = contacts_res.fetchone()
        contact_count = _scalar_zero(contact_count_row)

        sellers_res = await session.execute(
            text("SELECT COUNT(DISTINCT seller_name) FROM seller_contact_enrichment "
                 "WHERE contact_email IS NOT NULL")
        )
        sellers_row = sellers_res.fetchone()
        sellers_enriched = _scalar_zero(sellers_row)

        cost_res = await session.execute(
            text("SELECT COALESCE(SUM(cost_usd), 0) FROM enrichment_runs")
        )
        cost_row = cost_res.fetchone()
        cost_to_date = float(_scalar_zero(cost_row) or 0)

    never = sum(1 for r in queue_rows if r.get("freshness") == "never")
    stale = sum(1 for r in queue_rows if r.get("freshness") == "stale")
    top10 = [
        {
            "seller_name": r["seller_name"],
            "source": r.get("source"),
            "listing_volume": r.get("listing_volume"),
            "freshness": r.get("freshness"),
            "attempts": r.get("attempts", 0),
        }
        for r in queue_rows[:10]
    ]

    return {
        "queue": {
            "total_pending": len(queue_rows),
            "never_researched": never,
            "stale": stale,
            "top_10_by_listing_volume": top10,
        },
        "recent_runs": [
            {
                "run_id": str(r.get("run_id")),
                "started_at": _iso(r.get("started_at")),
                "finished_at": _iso(r.get("finished_at")),
                "trigger": r.get("trigger"),
                "provider_chain": r.get("provider_chain"),
                "sellers_total": r.get("sellers_total", 0),
                "sellers_succeeded": r.get("sellers_succeeded", 0),
                "sellers_failed": r.get("sellers_failed", 0),
                "contacts_added": r.get("contacts_added", 0),
                "cost_usd": float(r.get("cost_usd") or 0),
                "notes": r.get("notes"),
            }
            for r in run_rows
        ],
        "totals": {
            "sellers_enriched_all_time": int(sellers_enriched or 0),
            "contacts_in_db": int(contact_count or 0),
            "cost_to_date_usd": round(cost_to_date, 3),
        },
    }


@router.get("/v2/intel/queue")
async def intel_queue(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Paginated list of sellers pending research."""
    _require_admin(authorization)

    async with get_session() as session:
        res = await session.execute(_QUEUE_PAGED_SQL, {"lim": limit, "off": offset})
        rows = [_q_row(r) for r in res.fetchall()]

    return {
        "items": [
            {
                "seller_name": r["seller_name"],
                "source": r.get("source"),
                "listing_volume": r.get("listing_volume"),
                "last_seen": _iso(r.get("last_seen")),
                "last_researched_at": _iso(r.get("last_researched_at")),
                "attempts": r.get("attempts", 0),
                "freshness": r.get("freshness"),
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
    }


# ── helpers ──────────────────────────────────────────────────────────


def _q_row_run(row: Any) -> dict:
    if hasattr(row, "_data") and isinstance(row._data, dict):
        return dict(row._data)
    if isinstance(row, dict):
        return dict(row)
    return {
        "run_id": row[0],
        "started_at": row[1],
        "finished_at": row[2],
        "trigger": row[3],
        "provider_chain": row[4],
        "sellers_total": row[5],
        "sellers_succeeded": row[6],
        "sellers_failed": row[7],
        "contacts_added": row[8],
        "cost_usd": row[9],
        "notes": row[10],
    }


def _scalar_zero(row: Any) -> Any:
    """Pull the first column off a row (count / sum / coalesce queries)."""
    if row is None:
        return 0
    if hasattr(row, "_values"):
        return row._values[0] if row._values else 0
    if hasattr(row, "_data") and isinstance(row._data, dict):
        values = list(row._data.values())
        return values[0] if values else 0
    try:
        return row[0]
    except (KeyError, TypeError, IndexError):
        return 0
