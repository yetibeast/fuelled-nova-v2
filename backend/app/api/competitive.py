from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from app.db.session import get_session

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. GET /competitive/summary — real metric counts
# ---------------------------------------------------------------------------

@router.get("/competitive/summary")
async def competitive_summary():
    async with get_session() as session:
        # Total non-fuelled listings
        r1 = await session.execute(text(
            "SELECT COUNT(*) FROM listings WHERE LOWER(source) != 'fuelled'"
        ))
        competitor_total = r1.scalar() or 0

        # New this week (first_seen within 7 days)
        r2 = await session.execute(text(
            """SELECT COUNT(*) FROM listings
               WHERE first_seen >= NOW() - INTERVAL '7 days'
               AND LOWER(source) != 'fuelled'"""
        ))
        new_this_week = r2.scalar() or 0

        # Stale inventory: listed > 1 year, still active, with price
        r3 = await session.execute(text(
            """SELECT COUNT(*) FROM listings
               WHERE first_seen < NOW() - INTERVAL '365 days'
               AND last_seen > NOW() - INTERVAL '30 days'
               AND asking_price > 0"""
        ))
        stale_count = r3.scalar() or 0

    return {
        "competitor_total": competitor_total,
        "new_this_week": new_this_week,
        "stale_count": stale_count,
    }


# ---------------------------------------------------------------------------
# 2. GET /competitive/new — new listings this week
# ---------------------------------------------------------------------------

@router.get("/competitive/new")
async def competitive_new():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT title, source, asking_price, category_normalized,
                      location, url, first_seen
               FROM listings
               WHERE first_seen >= NOW() - INTERVAL '7 days'
               AND LOWER(source) != 'fuelled'
               AND asking_price > 0
               ORDER BY first_seen DESC
               LIMIT 25"""
        ))
        rows = result.fetchall()
    return [
        {
            "title": r[0], "source": r[1],
            "asking_price": float(r[2]) if r[2] else None,
            "category": r[3], "location": r[4], "url": r[5],
            "first_seen": str(r[6]) if r[6] else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 3. GET /competitive/stale — old unsold inventory
# ---------------------------------------------------------------------------

@router.get("/competitive/stale")
async def competitive_stale():
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT title, source, asking_price, category_normalized,
                      location, url, first_seen,
                      EXTRACT(DAY FROM NOW() - first_seen)::int as days_listed
               FROM listings
               WHERE first_seen < NOW() - INTERVAL '365 days'
               AND last_seen > NOW() - INTERVAL '30 days'
               AND asking_price > 0
               ORDER BY first_seen ASC
               LIMIT 25"""
        ))
        rows = result.fetchall()
    return [
        {
            "title": r[0], "source": r[1],
            "asking_price": float(r[2]) if r[2] else None,
            "category": r[3], "location": r[4], "url": r[5],
            "first_seen": str(r[6]) if r[6] else None,
            "days_listed": r[7],
        }
        for r in rows
    ]
