from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
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

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")


# ── User CRUD ──────────────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    name: str
    email: str
    role: str
    password: str


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None


@router.get("/users")
async def list_users(authorization: str = Header(None)):
    _require_admin(authorization)
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
async def create_user(body: CreateUserRequest, authorization: str = Header(None)):
    _require_admin(authorization)
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
async def update_user(user_id: str, body: UpdateUserRequest, authorization: str = Header(None)):
    _require_admin(authorization)
    updates, params = [], {"id": user_id}
    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.email is not None:
        updates.append("email = :email")
        params["email"] = body.email.strip().lower()
    if body.role is not None:
        updates.append("role = :role")
        params["role"] = body.role
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
    if body.password is not None:
        hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        updates.append("password_hash = :hash")
        params["hash"] = hashed
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


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, authorization: str = Header(None)):
    _require_admin(authorization)
    admin_id = _require_admin(authorization)
    if admin_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    async with get_session() as session:
        result = await session.execute(
            text("DELETE FROM users WHERE id = :id RETURNING id"),
            {"id": user_id},
        )
        row = result.fetchone()
        await session.commit()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True, "id": str(row[0])}


# ── Admin logs ─────────────────────────────────────────────────────────────


@router.get("/valuations")
async def admin_valuations(authorization: str = Header(None)):
    _require_admin(authorization)
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
async def admin_feedback(negative_only: bool = Query(default=False), authorization: str = Header(None)):
    _require_admin(authorization)
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
