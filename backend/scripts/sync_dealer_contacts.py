"""Sync dealer_contacts → listings.event_contact_* for surfacing in the
stale-targets CSV.

Idempotent. Re-run after every Kijiji/AllSurplus scrape until the CSV writer
is refactored to LEFT JOIN dealer_contacts directly (see [MORNING] task).

Usage:
    PYTHONPATH=backend python3 backend/scripts/sync_dealer_contacts.py [--dry-run]

Env: DATABASE_URL must be set (or pass --db-url).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


SYNC_SQL = text("""
    UPDATE listings l
    SET event_contact_name  = COALESCE(d.contact_name,  l.event_contact_name),
        event_contact_email = COALESCE(d.contact_email, l.event_contact_email),
        event_contact_phone = COALESCE(d.contact_phone, l.event_contact_phone)
    FROM dealer_contacts d
    WHERE l.seller_name = d.seller_name
      AND l.source      = d.source
      AND (
          (d.contact_name  IS NOT NULL AND l.event_contact_name  IS DISTINCT FROM d.contact_name)
       OR (d.contact_email IS NOT NULL AND l.event_contact_email IS DISTINCT FROM d.contact_email)
       OR (d.contact_phone IS NOT NULL AND l.event_contact_phone IS DISTINCT FROM d.contact_phone)
      )
    RETURNING l.id, l.source, l.seller_name
""")

PREVIEW_SQL = text("""
    SELECT d.seller_name, d.source,
           d.contact_name, d.contact_email, d.contact_phone,
           COUNT(l.id) AS matched_listings
    FROM dealer_contacts d
    LEFT JOIN listings l
      ON l.seller_name = d.seller_name AND l.source = d.source
    GROUP BY d.seller_name, d.source, d.contact_name, d.contact_email, d.contact_phone
    ORDER BY matched_listings DESC
""")


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    p.add_argument("--dry-run", action="store_true", help="Show what would change, don't write.")
    args = p.parse_args()

    if not args.db_url:
        print("ERROR: --db-url or DATABASE_URL required", file=sys.stderr)
        return 2

    url = args.db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)

    async with engine.connect() as conn:
        preview = (await conn.execute(PREVIEW_SQL)).fetchall()
        print(f"{'seller':<48} {'source':<12} {'matched':>8}  contact")
        for r in preview:
            contact = " | ".join(filter(None, [r[2], r[3], r[4]])) or "(empty)"
            print(f"{(r[0] or '')[:46]:<48} {r[1]:<12} {r[5]:>8}  {contact}")

        if args.dry_run:
            print("\nDRY RUN — no writes performed.")
            return 0

        updated = (await conn.execute(SYNC_SQL)).fetchall()
        await conn.commit()

        print(f"\nUpdated {len(updated)} listings rows from dealer_contacts.")
        by_source = {}
        for row in updated:
            by_source[row[1]] = by_source.get(row[1], 0) + 1
        for src, n in sorted(by_source.items(), key=lambda x: -x[1]):
            print(f"  {src:<14} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
