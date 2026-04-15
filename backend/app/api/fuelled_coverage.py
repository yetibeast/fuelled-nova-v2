"""Fuelled pricing-coverage analytics endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header
from sqlalchemy import text

from app.api.admin import _require_auth
from app.db.session import get_session

router = APIRouter(tags=["fuelled-coverage"])
_log = logging.getLogger(__name__)

# Table-creation guard (run once per process)
_table_init = False

# ── Canonical SQL fragments ───────────────────────────────────────────────

_BASE = "source = 'fuelled' AND is_active = true"
_HAS_ASKING = "asking_price > 0"
_HAS_VALUE = "(asking_price > 0 OR fair_value > 0)"
_AI_ONLY = "(fair_value > 0 AND NOT asking_price > 0)"
_TIER = """CASE
    WHEN make IS NOT NULL AND model IS NOT NULL AND year IS NOT NULL THEN 1
    WHEN make IS NOT NULL AND year IS NOT NULL THEN 2
    WHEN make IS NOT NULL THEN 3
    ELSE 4
END"""
_COMPLETENESS = """(
    CASE WHEN make IS NOT NULL THEN 25 ELSE 0 END +
    CASE WHEN model IS NOT NULL THEN 20 ELSE 0 END +
    CASE WHEN year IS NOT NULL THEN 25 ELSE 0 END +
    CASE WHEN hours IS NOT NULL THEN 15 ELSE 0 END +
    CASE WHEN horsepower IS NOT NULL THEN 10 ELSE 0 END +
    CASE WHEN condition IS NOT NULL THEN 5 ELSE 0 END
)"""


async def _ensure_table(session):
    """Create fuelled_valuations table if it doesn't exist yet."""
    global _table_init
    if _table_init:
        return
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS fuelled_valuations (
            id TEXT PRIMARY KEY,
            listing_id TEXT NOT NULL,
            fmv_low REAL,
            fmv_mid REAL,
            fmv_high REAL,
            confidence TEXT,
            method TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    await session.commit()
    _table_init = True


# ---------------------------------------------------------------------------
# GET /admin/fuelled/coverage
# ---------------------------------------------------------------------------

@router.get("/admin/fuelled/coverage")
async def fuelled_coverage_stats(authorization: str = Header(None)):
    """Return coverage statistics for Fuelled-sourced listings."""
    _require_auth(authorization)

    async with get_session() as session:
        await _ensure_table(session)

        # Main stats
        result = await session.execute(text(f"""
            SELECT
                COUNT(*),
                COUNT(CASE WHEN {_HAS_ASKING} THEN 1 END),
                COUNT(CASE WHEN {_HAS_VALUE} THEN 1 END),
                COUNT(CASE WHEN {_AI_ONLY} THEN 1 END),
                AVG({_COMPLETENESS})
            FROM listings
            WHERE {_BASE}
        """))
        row = result.fetchone()
        total = row[0] or 0
        asking_ct = row[1] or 0
        valued_ct = row[2] or 0
        ai_only_ct = row[3] or 0
        completeness_avg = round(row[4] or 0, 1)

        # Tier breakdown (unvalued only)
        result = await session.execute(text(f"""
            SELECT {_TIER} AS tier, COUNT(*) AS cnt
            FROM listings
            WHERE {_BASE} AND NOT {_HAS_VALUE}
            GROUP BY tier
            ORDER BY tier
        """))
        tier_rows = result.fetchall()
        by_tier = {f"tier_{r[0]}": r[1] for r in tier_rows} if tier_rows else {}

        # Category breakdown (unvalued, top 10)
        result = await session.execute(text(f"""
            SELECT category, COUNT(*) AS cnt
            FROM listings
            WHERE {_BASE} AND NOT {_HAS_VALUE}
            GROUP BY category
            ORDER BY cnt DESC
            LIMIT 10
        """))
        cat_rows = result.fetchall()
        by_category = [{"category": r[0], "count": r[1]} for r in cat_rows] if cat_rows else []

    unpriced = total - valued_ct

    return {
        "total": total,
        "asking_price_count": asking_ct,
        "asking_price_pct": round(asking_ct / total * 100, 1) if total else 0,
        "valued_count": valued_ct,
        "valued_pct": round(valued_ct / total * 100, 1) if total else 0,
        "ai_only_count": ai_only_ct,
        "unpriced": unpriced,
        "by_tier": by_tier,
        "by_category": by_category,
        "completeness_avg": completeness_avg,
    }
