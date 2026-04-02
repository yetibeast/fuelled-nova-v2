from __future__ import annotations

import jwt
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

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


@router.get("/scrapers")
async def list_scrapers(authorization: str = Header(None)):
    _require_admin(authorization)
    """List sources with listing counts and optional scrape run info."""
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT source,
                   COUNT(*) as total,
                   COUNT(CASE WHEN asking_price > 0 THEN 1 END) as with_price
            FROM listings
            GROUP BY source
            ORDER BY COUNT(*) DESC
        """))
        sources = []
        for row in result.fetchall():
            sources.append({
                "name": row[0],
                "total_listings": row[1],
                "with_price": row[2],
                "last_run_at": None,
                "last_run_status": None,
                "items_found": None,
                "items_new": None,
                "last_error": None,
            })

        # Enrich with scrape run info if tables exist
        try:
            runs = await session.execute(text("""
                SELECT DISTINCT ON (st.name)
                       st.name, sr.status, sr.started_at,
                       sr.items_found, sr.items_new, sr.error_message
                FROM scrape_runs sr
                JOIN scrape_targets st ON st.id = sr.target_id
                ORDER BY st.name, sr.started_at DESC
            """))
            run_map = {}
            for r in runs.fetchall():
                run_map[r[0]] = {
                    "last_run_at": r[2].isoformat() if r[2] else None,
                    "last_run_status": r[1],
                    "items_found": r[3],
                    "items_new": r[4],
                    "last_error": r[5],
                }
            for s in sources:
                if s["name"] in run_map:
                    s.update(run_map[s["name"]])
        except ProgrammingError:
            pass  # scrape_runs/scrape_targets tables may not exist yet

    return sources
