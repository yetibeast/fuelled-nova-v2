from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
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
    # COALESCE(asking_price, current_bid) lets auction sources (allsurplus,
    # bidspotter, govdeals, ironplanet partial) survive the gate — they price
    # via current_bid, not asking_price. Without this they were silently
    # dropped, hiding 175 captured AllSurplus seller_names from stale-targets.
    result = await session.execute(text(
        """SELECT id, title, source, asking_price, current_bid,
                  category_normalized, category,
                  make, model, year, condition, hours, horsepower,
                  location, url, first_seen, last_seen,
                  seller_name, seller_account_type, seller_other_assets_url,
                  event_contact_name, event_contact_email, event_contact_phone
           FROM listings
           WHERE LOWER(source) != 'fuelled'
           AND COALESCE(asking_price, current_bid, 0) > 0
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

        # Stale inventory headline count — approximates the per-category logic in
        # build_stale_candidate. 60 days is the most-permissive category threshold
        # (compressors/engines/generators); per-category filtering happens in
        # /competitive/stale-targets which scores and ranks the actual candidates.
        # COALESCE keeps this count consistent with _load_competitor_priced_rows
        # so auction sources (current_bid only) aren't silently dropped.
        r3 = await session.execute(text(
            """SELECT COUNT(*) FROM listings
               WHERE first_seen < NOW() - INTERVAL '60 days'
               AND last_seen > NOW() - INTERVAL '30 days'
               AND LOWER(source) != 'fuelled'
               AND COALESCE(asking_price, current_bid, 0) > 0"""
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
        # Surface ask-priced and bid-priced stale rows together; the
        # listing-level "asking_price" returned is whichever the source
        # actually populates (auction sources use current_bid).
        result = await session.execute(text(
            """SELECT title, source,
                      COALESCE(asking_price, current_bid) AS list_price,
                      category_normalized,
                      location, url, first_seen,
                      EXTRACT(DAY FROM NOW() - first_seen)::int as days_listed
               FROM listings
               WHERE first_seen < NOW() - INTERVAL '60 days'
               AND last_seen > NOW() - INTERVAL '30 days'
               AND LOWER(source) != 'fuelled'
               AND COALESCE(asking_price, current_bid, 0) > 0
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

def _cap_per_seller(candidates: list[dict], cap: int) -> list[dict]:
    """Single-pass cap: each non-null seller_name appears at most `cap` times,
    anonymous rows pass through unrestricted. cap=0 disables (legacy)."""
    if cap <= 0:
        return candidates
    seen: dict[str, int] = {}
    out: list[dict] = []
    for row in candidates:
        name = (row.get("seller_name") or "").strip()
        if not name:
            out.append(row)
            continue
        used = seen.get(name, 0)
        if used >= cap:
            continue
        seen[name] = used + 1
        out.append(row)
    return out


def _seller_diverse_order(candidates: list[dict], cap_named: int) -> list[dict]:
    """Two-pass ordering for the dashboard top-N. Surface distinct named
    sellers first (one row each by default), then fill remaining slots with
    anonymous rows and any over-cap named rows.

    Reason: anonymous high-quality dealer rows (equipmenttrader, no seller
    capture) tie at score=100 with named-but-lower-scored auction rows
    (allsurplus, source_score=0). A pure score sort buries every named
    auction seller. Mark explicitly asked for *names* to target, so we
    surface them first.
    """
    seen: dict[str, int] = {}
    named_section: list[dict] = []
    overflow: list[dict] = []
    for row in candidates:  # caller pre-sorts by score
        name = (row.get("seller_name") or "").strip()
        if not name:
            overflow.append(row)
            continue
        used = seen.get(name, 0)
        if used < cap_named:
            named_section.append(row)
            seen[name] = used + 1
        else:
            overflow.append(row)
    return named_section + overflow


@router.get("/competitive/stale-targets")
async def competitive_stale_targets(
    authorization: str = Header(None),
    promotable_only: bool = Query(False),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(25, ge=1, le=100),
    cap_per_seller: int = Query(1, ge=0, le=100),
    sort: str = Query("seller_diverse", pattern="^(seller_diverse|score_only)$"),
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

    if sort == "score_only":
        candidates = _cap_per_seller(candidates, cap_per_seller)
    else:
        candidates = _seller_diverse_order(candidates, max(cap_per_seller, 1))

    return candidates[:limit]


# ---------------------------------------------------------------------------
# 4b. GET /competitive/stale-targets.csv — same compute, CSV download
# ---------------------------------------------------------------------------
#
# Mark asked (2026-05-11) whether the stale-targets list could be exported so
# his team can work it offline. Mirrors the JSON endpoint's compute exactly;
# column set matches the on-screen table plus the fields outreach needs
# (contact email/phone, seller-other-assets URL).

_CSV_COLUMNS = [
    "rank",
    "title",
    "category",
    "source",
    "seller_name",
    "seller_account_type",
    "seller_other_assets_url",
    "contact_name",
    "contact_email",
    "contact_phone",
    "asking_price",
    "current_bid",
    "days_listed",
    "stale_threshold_days",
    "acquisition_score",
    "peer_median",
    "peer_count",
    "reason",
    "url",
]


@router.get("/competitive/stale-targets.csv")
async def competitive_stale_targets_csv(
    authorization: str = Header(None),
    promotable_only: bool = Query(False),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(500, ge=1, le=5000),
    cap_per_seller: int = Query(1, ge=0, le=100),
    sort: str = Query("seller_diverse", pattern="^(seller_diverse|score_only)$"),
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

    # Match the JSON dashboard endpoint's default ordering so the CSV
    # download reflects the same seller diversity Mark sees on the page.
    # Pass `?sort=score_only&cap_per_seller=0` to get the full legacy
    # pure-score list for offline working.
    candidates.sort(key=lambda row: (-row["acquisition_score"], -row["days_listed"]))
    if sort == "score_only":
        candidates = _cap_per_seller(candidates, cap_per_seller)
    else:
        candidates = _seller_diverse_order(candidates, max(cap_per_seller, 1))
    candidates = candidates[:limit]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for idx, c in enumerate(candidates, start=1):
        writer.writerow([
            idx,
            c.get("title") or "",
            c.get("category") or "",
            c.get("source") or "",
            c.get("seller_name") or "",
            c.get("seller_account_type") or "",
            c.get("seller_other_assets_url") or "",
            c.get("event_contact_name") or "",
            c.get("event_contact_email") or "",
            c.get("event_contact_phone") or "",
            c.get("asking_price") or "",
            c.get("current_bid") or "",
            c.get("days_listed") or "",
            c.get("stale_threshold_days") or "",
            c.get("acquisition_score") or "",
            c.get("peer_median") or "",
            c.get("peer_count") or "",
            c.get("reason") or "",
            c.get("url") or "",
        ])
    buf.seek(0)

    filename = f"stale_targets_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
