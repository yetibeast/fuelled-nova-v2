from __future__ import annotations

import jwt
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import text

from app.competitive_acquisition import build_stale_candidate, row_dict
from app.config import JWT_SECRET
from app.db.session import get_session

router = APIRouter()


def _require_auth(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


async def _load_competitor_priced_rows(session):
    result = await session.execute(text(
        """SELECT id, title, source, asking_price, category_normalized, category,
                  make, model, year, condition, hours, horsepower,
                  location, url, first_seen, last_seen
           FROM listings
           WHERE LOWER(source) != 'fuelled'
           AND asking_price > 0
           AND first_seen IS NOT NULL
           AND last_seen IS NOT NULL"""
    ))
    return [row_dict(row) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# 1. GET /competitive/summary — real metric counts
# ---------------------------------------------------------------------------

@router.get("/competitive/summary")
async def competitive_summary(authorization: str = Header(None)):
    _require_auth(authorization)
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
               AND LOWER(source) != 'fuelled'
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
async def competitive_new(authorization: str = Header(None)):
    _require_auth(authorization)
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
async def competitive_stale(authorization: str = Header(None)):
    _require_auth(authorization)
    async with get_session() as session:
        result = await session.execute(text(
            """SELECT title, source, asking_price, category_normalized,
                      location, url, first_seen,
                      EXTRACT(DAY FROM NOW() - first_seen)::int as days_listed
               FROM listings
               WHERE first_seen < NOW() - INTERVAL '365 days'
               AND last_seen > NOW() - INTERVAL '30 days'
               AND LOWER(source) != 'fuelled'
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


# ---------------------------------------------------------------------------
# 4. GET /competitive/stale-targets — ranked stale acquisition candidates
# ---------------------------------------------------------------------------

@router.get("/competitive/stale-targets")
async def competitive_stale_targets(
    authorization: str = Header(None),
    promotable_only: bool = Query(False),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(25, ge=1, le=100),
):
    _require_auth(authorization)
    async with get_session() as session:
        rows = await _load_competitor_priced_rows(session)

    candidates = []
    for row in rows:
        candidate = build_stale_candidate(row, rows)
        if candidate is None:
            continue
        if promotable_only and not candidate["promotable"]:
            continue
        if candidate["acquisition_score"] < min_score:
            continue
        candidates.append(candidate)

    candidates.sort(key=lambda row: (-row["acquisition_score"], -row["days_listed"]))
    return candidates[:limit]
