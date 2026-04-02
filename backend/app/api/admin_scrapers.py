"""Scraper management — CRUD targets, run history, harvest triggers."""
from __future__ import annotations

import logging
import os

import httpx
import jwt
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.config import JWT_SECRET
from app.db.session import get_session

router = APIRouter(prefix="/admin")
_log = logging.getLogger(__name__)

SCRAPER_RUNNER_URL = os.environ.get("SCRAPER_RUNNER_URL", "")

# ── Table creation ────────────────────────────────────────────────────────

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS scrape_targets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT UNIQUE NOT NULL,
    url               TEXT,
    status            TEXT NOT NULL DEFAULT 'active',
    scraper_type      TEXT NOT NULL DEFAULT 'scrapekit',
    schedule_cron     TEXT,
    last_run_at       TIMESTAMPTZ,
    next_run_at       TIMESTAMPTZ,
    run_requested_at  TIMESTAMPTZ,
    health_pct        INTEGER DEFAULT 100,
    total_items       INTEGER DEFAULT 0,
    items_with_price  INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id               UUID REFERENCES scrape_targets(id),
    site_name               TEXT NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    status                  TEXT NOT NULL DEFAULT 'running',
    items_found             INTEGER DEFAULT 0,
    items_new               INTEGER DEFAULT 0,
    items_updated           INTEGER DEFAULT 0,
    final_prices_harvested  INTEGER DEFAULT 0,
    error_message           TEXT,
    duration_ms             INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_target ON scrape_runs(target_id);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_site ON scrape_runs(site_name);
"""

_SEED_SQL = """
INSERT INTO scrape_targets (name, url, scraper_type, schedule_cron) VALUES
    ('machinio',             'https://www.machinio.com',        'scrapekit',   '0 */6 * * *'),
    ('ritchiebros',          'https://www.ritchiebros.com',     'scrapekit',   '0 */6 * * *'),
    ('surplusrecord',        'https://www.surplusrecord.com',   'scrapekit',   '0 */12 * * *'),
    ('energyauctions',       'https://www.energyauctions.com',  'scrapekit',   '0 */12 * * *'),
    ('allsurplus',           'https://www.allsurplus.com',      'scrapekit',   '0 */12 * * *'),
    ('ironplanet',           'https://www.ironplanet.com',      'scrapekit',   '0 */12 * * *'),
    ('govdeals',             'https://www.govdeals.com',        'scrapekit',   '0 */12 * * *'),
    ('bidspotter',           'https://www.bidspotter.com',      'scrapekit',   '0 */6 * * *'),
    ('equipmenttrader',      'https://www.equipmenttrader.com', 'scrapekit',   '0 */6 * * *'),
    ('kijiji',               'https://www.kijiji.ca',           'scrapekit',   '0 */6 * * *'),
    ('reflowx',              'https://www.reflowx.com',         'standalone',  '0 */6 * * *'),
    ('ironhub',              'https://www.ironhub.com',         'standalone',  '0 0 * * *'),
    ('fuelled',              'https://www.fuelled.com',          'standalone',  '0 */6 * * *'),
    ('sold_price_harvester', NULL,                               'harvester',   '0 2 * * *')
ON CONFLICT (name) DO NOTHING;
"""

_tables_ready = False


async def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    async with get_session() as session:
        await session.execute(text(_INIT_SQL))
        await session.commit()
        # Seed if empty
        result = await session.execute(text("SELECT COUNT(*) FROM scrape_targets"))
        count = result.scalar()
        if count == 0:
            await session.execute(text(_SEED_SQL))
            await session.commit()
    _tables_ready = True


# ── Auth ──────────────────────────────────────────────────────────────────

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


# ── Fire-and-forget webhook ───────────────────────────────────────────────

async def _notify_runner(path: str):
    """POST to Proxmox runner if SCRAPER_RUNNER_URL is configured."""
    if not SCRAPER_RUNNER_URL:
        return
    url = f"{SCRAPER_RUNNER_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url)
    except Exception as exc:
        _log.warning("Runner webhook failed (%s): %s", url, exc)


# ── Scraper Targets ──────────────────────────────────────────────────────

@router.get("/scrapers")
async def list_scrapers(authorization: str = Header(None)):
    """List all targets with listing counts and latest run info."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        # All targets
        targets = await session.execute(text("""
            SELECT id, name, url, status, scraper_type, schedule_cron,
                   last_run_at, next_run_at, run_requested_at,
                   health_pct, total_items, items_with_price, created_at
            FROM scrape_targets
            ORDER BY name
        """))
        target_rows = targets.fetchall()

        # Listing counts per source
        try:
            counts = await session.execute(text("""
                SELECT source,
                       COUNT(*) AS total,
                       COUNT(CASE WHEN asking_price > 0 THEN 1 END) AS with_price
                FROM listings
                GROUP BY source
            """))
            count_map = {r[0]: {"total_listings": r[1], "with_price": r[2]} for r in counts.fetchall()}
        except ProgrammingError:
            count_map = {}

        # Latest run per target
        try:
            runs = await session.execute(text("""
                SELECT DISTINCT ON (target_id)
                       target_id, status, started_at, completed_at,
                       items_found, items_new, items_updated, error_message, duration_ms
                FROM scrape_runs
                ORDER BY target_id, started_at DESC
            """))
            run_map = {}
            for r in runs.fetchall():
                run_map[str(r[0])] = {
                    "last_run_status": r[1],
                    "last_run_at": r[2].isoformat() if r[2] else None,
                    "last_run_completed": r[3].isoformat() if r[3] else None,
                    "items_found": r[4],
                    "items_new": r[5],
                    "items_updated": r[6],
                    "last_error": r[7],
                    "duration_ms": r[8],
                }
        except ProgrammingError:
            run_map = {}

    result = []
    for t in target_rows:
        tid = str(t[0])
        name = t[1]
        listing_info = count_map.get(name, {"total_listings": 0, "with_price": 0})
        run_info = run_map.get(tid, {})
        result.append({
            "id": tid,
            "name": name,
            "url": t[2],
            "status": t[3],
            "scraper_type": t[4],
            "schedule_cron": t[5],
            "last_run_at": t[6].isoformat() if t[6] else run_info.get("last_run_at"),
            "next_run_at": t[7].isoformat() if t[7] else None,
            "run_requested_at": t[8].isoformat() if t[8] else None,
            "health_pct": t[9],
            "total_items": t[10],
            "items_with_price": t[11],
            "created_at": t[12].isoformat() if t[12] else None,
            "total_listings": listing_info["total_listings"],
            "with_price": listing_info["with_price"],
            **{k: v for k, v in run_info.items() if k not in ("last_run_at",)},
        })

    return result


@router.post("/scrapers")
async def create_scraper(body: dict, authorization: str = Header(None)):
    """Create a new scraper target."""
    _require_admin(authorization)
    await _ensure_tables()

    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    async with get_session() as session:
        result = await session.execute(text("""
            INSERT INTO scrape_targets (name, url, scraper_type, schedule_cron)
            VALUES (:name, :url, :type, :cron)
            RETURNING id, name, url, scraper_type, schedule_cron, status, created_at
        """), {
            "name": name,
            "url": body.get("url"),
            "type": body.get("scraper_type", "scrapekit"),
            "cron": body.get("schedule_cron"),
        })
        row = result.fetchone()
        await session.commit()

    return {
        "id": str(row[0]),
        "name": row[1],
        "url": row[2],
        "scraper_type": row[3],
        "schedule_cron": row[4],
        "status": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
    }


@router.put("/scrapers/{target_id}")
async def update_scraper(target_id: str, body: dict, authorization: str = Header(None)):
    """Update a scraper target's fields."""
    _require_admin(authorization)
    await _ensure_tables()

    allowed = {"name", "url", "scraper_type", "schedule_cron", "status"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_parts = [f"{k} = :{k}" for k in updates]
    updates["tid"] = target_id

    async with get_session() as session:
        result = await session.execute(
            text(f"UPDATE scrape_targets SET {', '.join(set_parts)} WHERE id = :tid::uuid"),
            updates,
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")
        await session.commit()

    return {"status": "updated", "id": target_id}


@router.delete("/scrapers/{target_id}")
async def delete_scraper(target_id: str, authorization: str = Header(None)):
    """Delete a scraper target (hard delete)."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        # Delete runs first (FK constraint)
        await session.execute(
            text("DELETE FROM scrape_runs WHERE target_id = :tid::uuid"),
            {"tid": target_id},
        )
        result = await session.execute(
            text("DELETE FROM scrape_targets WHERE id = :tid::uuid"),
            {"tid": target_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")
        await session.commit()

    return {"status": "deleted", "id": target_id}


@router.post("/scrapers/{target_id}/run")
async def trigger_run(target_id: str, authorization: str = Header(None)):
    """Request an immediate scraper run."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(text("""
            UPDATE scrape_targets SET run_requested_at = NOW()
            WHERE id = :tid::uuid
            RETURNING name
        """), {"tid": target_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Target not found")
        name = row[0]
        await session.commit()

    await _notify_runner(f"run/{name}")
    return {"status": "run_requested", "id": target_id, "name": name}


@router.post("/scrapers/{target_id}/pause")
async def pause_scraper(target_id: str, authorization: str = Header(None)):
    """Pause a scraper target."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(
            text("UPDATE scrape_targets SET status = 'paused' WHERE id = :tid::uuid"),
            {"tid": target_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")
        await session.commit()

    return {"status": "paused", "id": target_id}


@router.post("/scrapers/{target_id}/resume")
async def resume_scraper(target_id: str, authorization: str = Header(None)):
    """Resume a paused scraper target."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(
            text("UPDATE scrape_targets SET status = 'active' WHERE id = :tid::uuid"),
            {"tid": target_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")
        await session.commit()

    return {"status": "active", "id": target_id}


# ── Scrape Runs ──────────────────────────────────────────────────────────

@router.get("/scrapers/runs/recent")
async def recent_runs(authorization: str = Header(None)):
    """Last 20 runs across all targets."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT sr.id, sr.target_id, sr.site_name, sr.started_at, sr.completed_at,
                   sr.status, sr.items_found, sr.items_new, sr.items_updated,
                   sr.final_prices_harvested, sr.error_message, sr.duration_ms
            FROM scrape_runs sr
            ORDER BY sr.started_at DESC
            LIMIT 20
        """))
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "target_id": str(r[1]),
            "site_name": r[2],
            "started_at": r[3].isoformat() if r[3] else None,
            "completed_at": r[4].isoformat() if r[4] else None,
            "status": r[5],
            "items_found": r[6],
            "items_new": r[7],
            "items_updated": r[8],
            "final_prices_harvested": r[9],
            "error_message": r[10],
            "duration_ms": r[11],
        }
        for r in rows
    ]


@router.get("/scrapers/{target_id}/runs")
async def target_runs(target_id: str, authorization: str = Header(None)):
    """Last 20 runs for a specific target."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, target_id, site_name, started_at, completed_at,
                   status, items_found, items_new, items_updated,
                   final_prices_harvested, error_message, duration_ms
            FROM scrape_runs
            WHERE target_id = :tid::uuid
            ORDER BY started_at DESC
            LIMIT 20
        """), {"tid": target_id})
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "target_id": str(r[1]),
            "site_name": r[2],
            "started_at": r[3].isoformat() if r[3] else None,
            "completed_at": r[4].isoformat() if r[4] else None,
            "status": r[5],
            "items_found": r[6],
            "items_new": r[7],
            "items_updated": r[8],
            "final_prices_harvested": r[9],
            "error_message": r[10],
            "duration_ms": r[11],
        }
        for r in rows
    ]


# ── Harvest ──────────────────────────────────────────────────────────────

@router.post("/scrapers/harvest")
async def trigger_harvest(authorization: str = Header(None)):
    """Trigger sold price harvest."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(text("""
            UPDATE scrape_targets SET run_requested_at = NOW()
            WHERE name = 'sold_price_harvester'
            RETURNING id
        """))
        row = result.fetchone()
        await session.commit()

    target_id = str(row[0]) if row else None
    await _notify_runner("harvest")
    return {"status": "harvest_requested", "target_id": target_id}


@router.get("/scrapers/harvest/stats")
async def harvest_stats(authorization: str = Header(None)):
    """Auction harvest statistics."""
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        try:
            result = await session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE auction_end < NOW()) AS total_closed,
                    COUNT(*) FILTER (WHERE auction_end < NOW() AND final_price IS NOT NULL) AS harvested,
                    COUNT(*) FILTER (WHERE auction_end < NOW() AND final_price IS NULL) AS remaining
                FROM listings
                WHERE auction_end IS NOT NULL
            """))
            row = result.fetchone()
            total_closed = row[0] if row else 0
            harvested = row[1] if row else 0
            remaining = row[2] if row else 0

            # Breakdown by source
            breakdown = await session.execute(text("""
                SELECT source, COUNT(*) AS cnt
                FROM listings
                WHERE auction_end < NOW()
                  AND auction_end IS NOT NULL
                  AND final_price IS NULL
                GROUP BY source
                ORDER BY cnt DESC
            """))
            sources = {r[0]: r[1] for r in breakdown.fetchall()}
        except ProgrammingError:
            total_closed = 0
            harvested = 0
            remaining = 0
            sources = {}

    return {
        "total_closed_auctions": total_closed,
        "harvested": harvested,
        "remaining": remaining,
        "sources": sources,
    }
