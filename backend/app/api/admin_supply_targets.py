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
    """Per-seller aggregate. Groups by `seller_name` when known, falls back to
    `seller_source_id` for anonymous sellers. The first URL number on AllSurplus
    is per-consignment, not per-organization, so name-based grouping is the
    accurate signal — multiple consignments from the same seller (e.g. ANCO,
    Assmang Khumani) collapse correctly."""
    _require_admin(authorization)

    where = ["seller_source_id IS NOT NULL"]
    params: dict = {"min_listings": min_listings, "limit": limit}
    if source:
        where.append("source = :source")
        params["source"] = source

    # Aggregation key: seller_name when present, else 'anon:' + seller_source_id.
    # `is_anonymous` lets the client distinguish real names from fallback ids.
    sql = f"""
        WITH seller_rows AS (
            SELECT
                source,
                seller_source_id,
                seller_name,
                seller_account_type,
                seller_other_assets_url,
                event_id, event_contact_name, event_contact_email, event_contact_phone,
                asking_price, current_bid,
                location, last_seen,
                COALESCE(seller_name, 'anon:' || seller_source_id) AS seller_key
            FROM listings
            WHERE {' AND '.join(where)}
        )
        SELECT
            source,
            seller_key,
            (seller_name IS NULL) AS is_anonymous,
            MAX(seller_name) AS seller_name,
            (ARRAY_AGG(seller_account_type) FILTER (WHERE seller_account_type IS NOT NULL))[1] AS account_type,
            (ARRAY_AGG(seller_other_assets_url) FILTER (WHERE seller_other_assets_url IS NOT NULL))[1] AS other_assets_url,
            (ARRAY_AGG(event_contact_name) FILTER (WHERE event_contact_name IS NOT NULL))[1] AS contact_name,
            (ARRAY_AGG(event_contact_email) FILTER (WHERE event_contact_email IS NOT NULL))[1] AS contact_email,
            (ARRAY_AGG(event_contact_phone) FILTER (WHERE event_contact_phone IS NOT NULL))[1] AS contact_phone,
            COUNT(DISTINCT event_id) AS event_count,
            COUNT(DISTINCT seller_source_id) AS consignment_count,
            COUNT(*) AS listing_count,
            COUNT(asking_price) FILTER (WHERE asking_price > 0) AS priced_count,
            ROUND(SUM(asking_price) FILTER (WHERE asking_price > 0)::numeric, 0) AS total_asking,
            ROUND(SUM(current_bid) FILTER (WHERE current_bid > 0)::numeric, 0) AS total_current_bid,
            MAX(last_seen) AS last_seen
        FROM seller_rows
        GROUP BY source, seller_key, (seller_name IS NULL)
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
            "seller_key": r[1],
            "is_anonymous": bool(r[2]),
            "seller_name": r[3],
            "account_type": r[4],
            "other_assets_url": r[5],
            "contact_name": r[6],
            "contact_email": r[7],
            "contact_phone": r[8],
            "event_count": int(r[9] or 0),
            "consignment_count": int(r[10]),
            "listing_count": int(r[11]),
            "priced_count": int(r[12] or 0),
            "total_asking": float(r[13]) if r[13] is not None else None,
            "total_current_bid": float(r[14]) if r[14] is not None else None,
            "last_seen": r[15].isoformat() if r[15] else None,
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
                   asking_price, currency, location, url, last_seen,
                   event_id, event_title, event_contact_name, event_contact_email, event_contact_phone
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
            "event_id": r[12],
            "event_title": r[13],
            "contact_name": r[14],
            "contact_email": r[15],
            "contact_phone": r[16],
        }
        for r in rows
    ]
