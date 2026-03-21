from __future__ import annotations

import json
import os
from datetime import datetime

import bcrypt
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import get_session

router = APIRouter(prefix="/admin")

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")


# ── User CRUD ──────────────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    name: str
    email: str
    role: str
    password: str


class UpdateUserRequest(BaseModel):
    role: str | None = None
    status: str | None = None


@router.get("/users")
async def list_users():
    async with get_session() as session:
        result = await session.execute(text(
            "SELECT id, name, email, role, status, last_login_at, created_at "
            "FROM users ORDER BY created_at"
        ))
        rows = result.fetchall()

    def _iso(val: object) -> str | None:
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val) if val is not None else None

    return [
        {
            "id": str(r[0]), "name": r[1], "email": r[2], "role": r[3],
            "status": r[4], "last_login_at": _iso(r[5]), "created_at": _iso(r[6]),
        }
        for r in rows
    ]


@router.post("/users")
async def create_user(body: CreateUserRequest):
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    async with get_session() as session:
        result = await session.execute(
            text(
                "INSERT INTO users (name, email, role, password_hash, status) "
                "VALUES (:name, :email, :role, :hash, 'active') RETURNING id, created_at"
            ),
            {"name": body.name, "email": body.email.strip().lower(),
             "role": body.role, "hash": hashed},
        )
        row = result.fetchone()
        await session.commit()

    return {
        "id": str(row[0]), "name": body.name,
        "email": body.email.strip().lower(), "role": body.role,
        "status": "active", "created_at": row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]),
    }


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest):
    updates, params = [], {"id": user_id}
    if body.role is not None:
        updates.append("role = :role")
        params["role"] = body.role
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    async with get_session() as session:
        result = await session.execute(
            text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id "
                 "RETURNING id, name, email, role, status"),
            params,
        )
        row = result.fetchone()
        await session.commit()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(row[0]), "name": row[1], "email": row[2],
            "role": row[3], "status": row[4]}


# ── Admin logs ─────────────────────────────────────────────────────────────


@router.get("/valuations")
async def admin_valuations():
    path = os.path.join(_LOG_DIR, "pricing_log.jsonl")
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            val = row.get("structured", {}).get("valuation", {})
            entries.append({
                "timestamp": row.get("timestamp"),
                "user_message": row.get("user_message", ""),
                "tools_used": row.get("tools_used", []),
                "confidence": row.get("confidence"),
                "fmv_low": val.get("fmv_low"),
                "fmv_mid": val.get("fmv_mid"),
                "fmv_high": val.get("fmv_high"),
                "response_length": row.get("response_length"),
            })
    entries.reverse()
    return entries[:50]


@router.get("/feedback")
async def admin_feedback(negative_only: bool = Query(default=False)):
    path = os.path.join(_LOG_DIR, "feedback_log.jsonl")
    if not os.path.exists(path):
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if negative_only and row.get("rating") != "down":
                continue
            sd = row.get("structured_data") or {}
            val = sd.get("valuation") or {}
            entries.append({
                "timestamp": row.get("timestamp"),
                "rating": row.get("rating"),
                "comment": row.get("comment"),
                "user_message": row.get("user_message", ""),
                "fmv_low": val.get("fmv_low"),
                "fmv_mid": val.get("fmv_mid"),
                "fmv_high": val.get("fmv_high"),
            })
    entries.reverse()
    return entries[:100]
