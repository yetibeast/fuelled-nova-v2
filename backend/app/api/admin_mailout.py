"""GET /api/admin/mailout/sellers.csv — aggregated mailout export.

One row per unique (source, seller_name) across the entire `listings` table.
Used as input to Mark's outreach / mailout tools. Single deduplicated list,
every captured seller / auction house / dealer Fuelled knows about.

Admin-only. JWT-gated via the shared `_require_admin` helper.

Aggregations per (source, seller_name) group:
  • total_listings          — COUNT(*)
  • active_listings_30d     — COUNT(*) FILTER WHERE last_seen >= NOW() - 30d
  • first_seen_on_fuelled   — MIN(first_seen)
  • last_seen_on_fuelled    — MAX(last_seen)
  • categories              — STRING_AGG(DISTINCT category_normalized), capped at 5
  • total_ask_value_usd     — SUM(COALESCE(asking_price, current_bid, 0))
  • contact_*, urls         — MAX(...) picks any non-null (contact info is
                              constant per seller, so MAX is deterministic)

NULL or empty `seller_name` rows are excluded.

Default sort: total_listings DESC, source, seller_name.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Header, Query
from fastapi.responses import Response
from sqlalchemy import text

from app.api.admin import _require_admin
from app.db.session import get_session

router = APIRouter()
_log = logging.getLogger(__name__)


_CSV_COLUMNS: list[str] = [
    "source",
    "seller_name",
    "account_type",
    "total_listings",
    "active_listings_30d",
    "first_seen_on_fuelled",
    "last_seen_on_fuelled",
    "categories",
    "total_ask_value_usd",
    "contact_name",
    "contact_email",
    "contact_phone",
    "other_assets_url",
    "sample_listing_url",
]


_AGGREGATE_SQL = """
SELECT
    source,
    seller_name,
    MAX(seller_account_type) AS account_type,
    COUNT(*) AS total_listings,
    COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '30 days') AS active_listings_30d,
    MIN(first_seen)::date AS first_seen_on_fuelled,
    MAX(last_seen)::date AS last_seen_on_fuelled,
    (
        SELECT STRING_AGG(c, ', ')
        FROM (
            SELECT DISTINCT category_normalized AS c
            FROM listings l2
            WHERE l2.source = l.source
              AND l2.seller_name = l.seller_name
              AND l2.category_normalized IS NOT NULL
            ORDER BY c
            LIMIT 6
        ) sub
    ) AS categories_raw,
    SUM(COALESCE(asking_price, current_bid, 0))::bigint AS total_ask_value_usd,
    MAX(event_contact_name) AS contact_name,
    MAX(event_contact_email) AS contact_email,
    MAX(event_contact_phone) AS contact_phone,
    MAX(seller_other_assets_url) AS other_assets_url,
    MAX(url) AS sample_listing_url
FROM listings l
WHERE seller_name IS NOT NULL
  AND seller_name <> ''
  {source_filter}
  {account_type_filter}
GROUP BY source, seller_name
{having_clause}
ORDER BY total_listings DESC, source, seller_name
LIMIT :limit
"""


def _cap_categories(raw: str | None) -> str:
    """Cap the comma-joined category string at 5 distinct values, then '...'."""
    if not raw:
        return ""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) <= 5:
        return ", ".join(parts)
    return ", ".join(parts[:5]) + ", ..."


@router.get("/admin/mailout/sellers.csv")
async def mailout_sellers_csv(
    authorization: str = Header(default=""),
    source: str | None = Query(default=None, description="Filter to a single source (e.g. 'kijiji')."),
    account_type: str | None = Query(default=None, description="Filter to one seller_account_type."),
    min_active: int = Query(default=0, ge=0, description="Drop sellers with < N active listings in last 30 days."),
    limit: int = Query(default=5000, ge=1, le=50000, description="Cap output rows."),
):
    """Aggregated seller export. Admin-only.

    Returns text/csv with header row + one row per unique (source, seller_name).
    """
    _require_admin(authorization)

    params: dict[str, Any] = {"limit": limit}
    source_filter = ""
    account_type_filter = ""
    having_clause = ""
    if source:
        source_filter = "AND source = :source"
        params["source"] = source
    if account_type:
        account_type_filter = "AND seller_account_type = :account_type"
        params["account_type"] = account_type
    if min_active > 0:
        having_clause = "HAVING COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '30 days') >= :min_active"
        params["min_active"] = min_active

    sql = _AGGREGATE_SQL.format(
        source_filter=source_filter,
        account_type_filter=account_type_filter,
        having_clause=having_clause,
    )

    async with get_session() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    for r in rows:
        # Row may be a Row (tuple) or a Mapping; access by index for compatibility
        # with both real SQLAlchemy rows and the test MockRow shim.
        writer.writerow([
            r[0] or "",                           # source
            r[1] or "",                           # seller_name
            r[2] or "",                           # account_type
            int(r[3]) if r[3] is not None else 0, # total_listings
            int(r[4]) if r[4] is not None else 0, # active_listings_30d
            r[5].isoformat() if r[5] else "",     # first_seen_on_fuelled
            r[6].isoformat() if r[6] else "",     # last_seen_on_fuelled
            _cap_categories(r[7]),                # categories
            int(r[8]) if r[8] is not None else 0, # total_ask_value_usd
            r[9] or "",                           # contact_name
            r[10] or "",                          # contact_email
            r[11] or "",                          # contact_phone
            r[12] or "",                          # other_assets_url
            r[13] or "",                          # sample_listing_url
        ])

    today = date.today().isoformat()
    filename = f"mailout_sellers_{today}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
