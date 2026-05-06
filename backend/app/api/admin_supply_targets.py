"""Supply-targets aggregation — per-seller view of scraped listings.

Driven by Mark Le Dain's 2026-05-05 "List of Supply Targets" ask: he wants a
list of every seller we've seen on a competitor marketplace, what they're
selling, and how to reach them. Phase 1 captures everything that's publicly
visible (no login required); Phase 2 will add authenticated capture for
email contacts.
"""
from __future__ import annotations

from typing import Optional

import jwt
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import text

from app.config import JWT_SECRET
from app.db.session import get_session

router = APIRouter(prefix="/admin")


def _require_admin(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return payload["sub"]


@router.get("/supply-targets")
async def supply_targets(
    authorization: str = Header(None),
    source: Optional[str] = Query(None, description="Filter to a single marketplace, e.g. 'allsurplus'"),
    min_listings: int = Query(1, ge=1, description="Drop sellers with fewer than this many listings"),
    limit: int = Query(500, ge=1, le=5000),
):
    """Per-seller aggregate. One row per (source, seller_source_id) — the seller_source_id
    falls back to a synthetic 'anon-<n>' grouping when we couldn't extract one (rare;
    most marketplaces embed the seller in the URL)."""
    _require_admin(authorization)

    where = ["seller_source_id IS NOT NULL"]
    params: dict = {"min_listings": min_listings, "limit": limit}
    if source:
        where.append("source = :source")
        params["source"] = source

    sql = f"""
        WITH seller_rows AS (
            SELECT
                source,
                seller_source_id,
                seller_name,
                seller_account_type,
                seller_other_assets_url,
                asking_price,
                location,
                last_seen
            FROM listings
            WHERE {' AND '.join(where)}
        )
        SELECT
            source,
            seller_source_id,
            -- Take the most common non-null name we've seen for this seller
            (SELECT seller_name FROM seller_rows s2
             WHERE s2.source = s.source AND s2.seller_source_id = s.seller_source_id
               AND seller_name IS NOT NULL
             GROUP BY seller_name ORDER BY COUNT(*) DESC LIMIT 1) AS seller_name,
            (SELECT seller_account_type FROM seller_rows s2
             WHERE s2.source = s.source AND s2.seller_source_id = s.seller_source_id
               AND seller_account_type IS NOT NULL
             GROUP BY seller_account_type ORDER BY COUNT(*) DESC LIMIT 1) AS account_type,
            (SELECT seller_other_assets_url FROM seller_rows s2
             WHERE s2.source = s.source AND s2.seller_source_id = s.seller_source_id
               AND seller_other_assets_url IS NOT NULL
             LIMIT 1) AS other_assets_url,
            COUNT(*) AS listing_count,
            COUNT(asking_price) FILTER (WHERE asking_price > 0) AS priced_count,
            ROUND(SUM(asking_price) FILTER (WHERE asking_price > 0)::numeric, 0) AS total_asking,
            MAX(last_seen) AS last_seen
        FROM seller_rows s
        GROUP BY source, seller_source_id
        HAVING COUNT(*) >= :min_listings
        ORDER BY listing_count DESC, total_asking DESC NULLS LAST
        LIMIT :limit
    """

    async with get_session() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()

    return [
        {
            "source": r[0],
            "seller_source_id": r[1],
            "seller_name": r[2],
            "account_type": r[3],
            "other_assets_url": r[4],
            "listing_count": int(r[5]),
            "priced_count": int(r[6] or 0),
            "total_asking": float(r[7]) if r[7] is not None else None,
            "last_seen": r[8].isoformat() if r[8] else None,
        }
        for r in rows
    ]


@router.get("/supply-targets/{source}/{seller_source_id}/listings")
async def supply_target_listings(
    source: str,
    seller_source_id: str,
    authorization: str = Header(None),
    limit: int = Query(200, ge=1, le=2000),
):
    """Drilldown: every listing we've seen from one (source, seller_source_id) pair."""
    _require_admin(authorization)
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, title, category, make, model, year, condition,
                   asking_price, currency, location, url, last_seen
            FROM listings
            WHERE source = :source AND seller_source_id = :sid
            ORDER BY last_seen DESC NULLS LAST
            LIMIT :limit
        """), {"source": source, "sid": seller_source_id, "limit": limit})
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "category": r[2],
            "make": r[3],
            "model": r[4],
            "year": r[5],
            "condition": r[6],
            "asking_price": float(r[7]) if r[7] is not None else None,
            "currency": r[8],
            "location": r[9],
            "url": r[10],
            "last_seen": r[11].isoformat() if r[11] else None,
        }
        for r in rows
    ]
