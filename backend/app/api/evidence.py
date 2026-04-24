"""Evidence flywheel — auto-capture valuations, flag reviews, promote to gold."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from app.config import JWT_SECRET, LOG_DIR as _LOG_DIR
from app.db.session import get_session

router = APIRouter(tags=["evidence"])

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS pricing_evidence_intake (
    id              TEXT PRIMARY KEY,
    source_file     TEXT NOT NULL DEFAULT 'nova_v2_valuation',
    manufacturer    TEXT,
    model           TEXT,
    category        TEXT,
    price_value     REAL,
    price_type      TEXT DEFAULT 'FMV',
    currency        TEXT DEFAULT 'CAD',
    confidence      TEXT,
    tools_used      TEXT,
    user_message    TEXT,
    structured_data JSONB,
    review_flag     TEXT DEFAULT 'auto_capture',
    comment         TEXT,
    user_corrected_fmv REAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_tables_ready = False


async def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    async with get_session() as session:
        await session.execute(text(_INIT_SQL))
        await session.commit()
    _tables_ready = True


def _get_user_id(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


def _require_admin(authorization: str | None) -> str:
    uid = _get_user_id(authorization)
    token = authorization[7:]  # type: ignore[index]
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return uid


# ── POST /api/evidence/capture ───────────────────────────────

@router.post("/evidence/capture")
async def capture_evidence(body: dict, authorization: str = Header(None)):
    _get_user_id(authorization)
    await _ensure_tables()

    structured = body.get("structured_data", {})
    valuation = structured.get("valuation", {})

    eid = "ev_" + uuid.uuid4().hex[:12]
    try:
        async with get_session() as session:
            await session.execute(text("""
                INSERT INTO pricing_evidence_intake
                    (id, source_id, raw_manufacturer, raw_model, equipment_category,
                     price_value, confidence, notes, price_type)
                VALUES (:id::uuid, (SELECT id FROM sources LIMIT 1),
                        :mfr, :model, :cat, :price, :conf, :notes, 'fmv')
            """), {
                "id": str(uuid.uuid4()),
                "mfr": valuation.get("manufacturer", ""),
                "model": valuation.get("model", ""),
                "cat": valuation.get("category", ""),
                "price": valuation.get("fmv_mid") or valuation.get("fmv_low"),
                "conf": body.get("confidence", "LOW"),
                "notes": body.get("user_message", ""),
            })
            await session.commit()
    except Exception:
        pass  # Non-critical — don't break pricing over evidence logging

    return {"evidence_id": eid}


# ── POST /api/evidence/flag-review ───────────────────────────

@router.post("/evidence/flag-review")
async def flag_review(body: dict, authorization: str = Header(None)):
    _get_user_id(authorization)
    await _ensure_tables()

    eid = body.get("evidence_id")
    if not eid:
        raise HTTPException(status_code=400, detail="evidence_id required")

    async with get_session() as session:
        result = await session.execute(
            text("SELECT id FROM pricing_evidence_intake WHERE id = :id"),
            {"id": eid},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Evidence not found")

        params: dict = {"id": eid, "comment": body.get("comment", "")}
        sql = "UPDATE pricing_evidence_intake SET review_flag = 'needs_review', comment = :comment"
        correction = body.get("user_correction")
        if correction is not None:
            sql += ", user_corrected_fmv = :correction"
            params["correction"] = float(correction)
        sql += " WHERE id = :id"

        await session.execute(text(sql), params)
        await session.commit()

    return {"status": "flagged"}


# ── GET /api/admin/evidence/review-queue ─────────────────────

@router.get("/admin/evidence/review-queue")
async def review_queue(authorization: str = Header(None)):
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, manufacturer, model, category, price_value, confidence,
                   user_message, structured_data, comment, user_corrected_fmv,
                   created_at
            FROM pricing_evidence_intake
            WHERE review_flag = 'needs_review'
            ORDER BY created_at DESC
            LIMIT 50
        """))
        rows = result.fetchall()

    return [
        {
            "id": r.id,
            "manufacturer": r.manufacturer,
            "model": r.model,
            "category": r.category,
            "price_value": r.price_value,
            "confidence": r.confidence,
            "user_message": r.user_message,
            "structured_data": r.structured_data,
            "comment": r.comment,
            "user_corrected_fmv": r.user_corrected_fmv,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── POST /api/admin/evidence/promote/:id ─────────────────────

@router.post("/admin/evidence/promote/{evidence_id}")
async def promote_evidence(evidence_id: str, authorization: str = Header(None)):
    _require_admin(authorization)
    await _ensure_tables()

    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM pricing_evidence_intake WHERE id = :id"),
            {"id": evidence_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evidence not found")

        await session.execute(
            text("UPDATE pricing_evidence_intake SET review_flag = 'promoted' WHERE id = :id"),
            {"id": evidence_id},
        )
        await session.commit()

    return {"status": "promoted", "id": evidence_id}
