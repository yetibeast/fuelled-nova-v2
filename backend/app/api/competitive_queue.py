from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query
from sqlalchemy import text

from app.api.admin import _require_admin
from app.api.competitive import _load_competitor_priced_rows
from app.competitive_acquisition import (
    build_draft_payload,
    build_stale_candidate,
    row_dict,
    target_record_from_candidate,
)
from app.db.session import get_session
from app.db.state_session import get_state_session

router = APIRouter(tags=["competitive-acquisition"])

_state_tables_ready = False
_STATUSES = ("new", "watching", "contacted", "negotiating", "drafted", "won", "lost", "archived")


async def _ensure_state_tables(session):
    global _state_tables_ready
    if _state_tables_ready:
        return
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS competitive_acquisition_targets (
            id TEXT PRIMARY KEY,
            source_listing_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT,
            asking_price DOUBLE PRECISION,
            location TEXT,
            url TEXT,
            first_seen TEXT,
            last_seen TEXT,
            days_listed INTEGER,
            stale_threshold_days INTEGER,
            peer_median DOUBLE PRECISION,
            peer_count INTEGER,
            acquisition_score INTEGER NOT NULL,
            promotable BOOLEAN NOT NULL DEFAULT TRUE,
            status TEXT NOT NULL DEFAULT 'new',
            assigned_to TEXT,
            notes TEXT,
            draft_payload TEXT,
            make TEXT,
            model TEXT,
            year INTEGER,
            condition TEXT,
            hours DOUBLE PRECISION,
            horsepower DOUBLE PRECISION,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS competitive_acquisition_events (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_note TEXT,
            actor_id TEXT,
            created_at TEXT NOT NULL
        )
    """))
    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_acq_targets_status ON competitive_acquisition_targets(status)"))
    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_acq_targets_source_listing_id ON competitive_acquisition_targets(source_listing_id)"))
    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_acq_targets_updated_at ON competitive_acquisition_targets(updated_at)"))
    await session.commit()
    _state_tables_ready = True


def _serialize_target(row) -> dict:
    target = row_dict(row)
    if isinstance(target.get("draft_payload"), str) and target["draft_payload"]:
        target["draft_payload"] = json.loads(target["draft_payload"])
    return target


async def _record_event(session, target_id: str, event_type: str, actor_id: str, note: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    await session.execute(
        text("""
            INSERT INTO competitive_acquisition_events (id, target_id, event_type, event_note, actor_id, created_at)
            VALUES (:id, :target_id, :event_type, :event_note, :actor_id, :created_at)
        """),
        {
            "id": f"evt_{uuid.uuid4().hex}",
            "target_id": target_id,
            "event_type": event_type,
            "event_note": note,
            "actor_id": actor_id,
            "created_at": now,
        },
    )


@router.get("/admin/competitive/acquisition/summary")
async def acquisition_summary(authorization: str = Header(None)):
    _require_admin(authorization)
    counts = {status: 0 for status in _STATUSES}
    async with get_state_session() as session:
        await _ensure_state_tables(session)
        result = await session.execute(text(
            "SELECT status, COUNT(*) AS cnt FROM competitive_acquisition_targets GROUP BY status"
        ))
        for row in result.fetchall():
            status = row[0]
            counts[status] = row[1]
    return {"total": sum(counts.values()), **counts}


@router.get("/admin/competitive/acquisition/targets")
async def acquisition_targets(
    authorization: str = Header(None),
    status: Optional[str] = Query(None),
):
    _require_admin(authorization)
    async with get_state_session() as session:
        await _ensure_state_tables(session)
        if status:
            result = await session.execute(
                text("SELECT * FROM competitive_acquisition_targets ORDER BY updated_at DESC"),
                {"status": status},
            )
        else:
            result = await session.execute(text("SELECT * FROM competitive_acquisition_targets ORDER BY updated_at DESC"))
        rows = [_serialize_target(row) for row in result.fetchall()]
    if status:
        rows = [row for row in rows if row.get("status") == status]
    return rows


@router.post("/admin/competitive/acquisition/promote")
async def promote_acquisition_target(body: dict = Body(...), authorization: str = Header(None)):
    admin_id = _require_admin(authorization)
    source_listing_id = body.get("source_listing_id")
    if not source_listing_id:
        raise HTTPException(status_code=400, detail="source_listing_id required")

    async with get_state_session() as state_session:
        await _ensure_state_tables(state_session)
        existing = await state_session.execute(
            text("SELECT * FROM competitive_acquisition_targets WHERE source_listing_id = :source_listing_id"),
            {"source_listing_id": source_listing_id},
        )
        row = existing.fetchone()
        if row:
            return _serialize_target(row)

    async with get_session() as listings_session:
        listings = await _load_competitor_priced_rows(listings_session)
    source_row = next((row for row in listings if row.get("id") == source_listing_id), None)
    if not source_row:
        raise HTTPException(status_code=404, detail="Source listing not found")

    candidate = build_stale_candidate(source_row, listings)
    if not candidate or not candidate["promotable"]:
        raise HTTPException(status_code=409, detail="Listing is not promotable as an acquisition target")

    record = target_record_from_candidate(candidate, body.get("note"))
    async with get_state_session() as state_session:
        await state_session.execute(text("""
            INSERT INTO competitive_acquisition_targets (
                id, source_listing_id, source, title, category, asking_price, location, url,
                first_seen, last_seen, days_listed, stale_threshold_days, peer_median, peer_count,
                acquisition_score, promotable, status, assigned_to, notes, draft_payload,
                make, model, year, condition, hours, horsepower, created_at, updated_at
            ) VALUES (
                :id, :source_listing_id, :source, :title, :category, :asking_price, :location, :url,
                :first_seen, :last_seen, :days_listed, :stale_threshold_days, :peer_median, :peer_count,
                :acquisition_score, :promotable, :status, :assigned_to, :notes, :draft_payload,
                :make, :model, :year, :condition, :hours, :horsepower, :created_at, :updated_at
            )
        """), record)
        await _record_event(state_session, record["id"], "promoted", admin_id, body.get("note"))
        await state_session.commit()
    return record


@router.post("/admin/competitive/acquisition/{target_id}/status")
async def update_acquisition_status(target_id: str, body: dict = Body(...), authorization: str = Header(None)):
    admin_id = _require_admin(authorization)
    status = body.get("status")
    if status not in _STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    async with get_state_session() as session:
        await _ensure_state_tables(session)
        existing = await session.execute(
            text("SELECT * FROM competitive_acquisition_targets WHERE id = :target_id"),
            {"target_id": target_id},
        )
        row = existing.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Target not found")
        updated_at = datetime.now(timezone.utc).isoformat()
        await session.execute(
            text("""
                UPDATE competitive_acquisition_targets
                SET status = :status, assigned_to = :assigned_to, notes = :notes, updated_at = :updated_at
                WHERE id = :target_id
            """),
            {
                "target_id": target_id,
                "status": status,
                "assigned_to": body.get("assigned_to"),
                "notes": body.get("notes"),
                "updated_at": updated_at,
            },
        )
        await _record_event(session, target_id, f"status:{status}", admin_id, body.get("notes"))
        await session.commit()

    target = _serialize_target(row)
    target["status"] = status
    target["assigned_to"] = body.get("assigned_to")
    target["notes"] = body.get("notes")
    target["updated_at"] = updated_at
    return target


@router.post("/admin/competitive/acquisition/{target_id}/draft")
async def generate_acquisition_draft(target_id: str, authorization: str = Header(None)):
    admin_id = _require_admin(authorization)
    async with get_state_session() as session:
        await _ensure_state_tables(session)
        existing = await session.execute(
            text("SELECT * FROM competitive_acquisition_targets WHERE id = :target_id"),
            {"target_id": target_id},
        )
        row = existing.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Target not found")
        target = _serialize_target(row)
        draft_payload = build_draft_payload(target)
        updated_at = datetime.now(timezone.utc).isoformat()
        await session.execute(
            text("""
                UPDATE competitive_acquisition_targets
                SET draft_payload = :draft_payload, updated_at = :updated_at
                WHERE id = :target_id
            """),
            {
                "target_id": target_id,
                "draft_payload": json.dumps(draft_payload),
                "updated_at": updated_at,
            },
        )
        await _record_event(session, target_id, "drafted", admin_id)
        await session.commit()
    return {"id": target_id, "draft_payload": draft_payload}
