"""Conversation persistence — CRUD over PostgreSQL conversations + messages."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.config import JWT_SECRET
from app.db.session import get_session

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Auth helper ──────────────────────────────────────────────────────────────

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


# ── Request models ───────────────────────────────────────────────────────────

class NewConversation(BaseModel):
    title: str = "New conversation"


class NewMessage(BaseModel):
    role: str  # "user" | "nova"
    text: Optional[str] = None
    data: Optional[dict] = None


# ── Ensure tables ────────────────────────────────────────────────────────────

_INIT_SQLS = [
    # Add missing columns to existing conversations table (V1 has uuid id, query, agent_used)
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'New conversation'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id VARCHAR(100)",
    """CREATE TABLE IF NOT EXISTS conversation_messages (
        id              TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role            TEXT NOT NULL,
        text            TEXT,
        data            JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_msg_conv ON conversation_messages(conversation_id)",
]

_tables_ready = False


async def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    try:
        async with get_session() as session:
            for stmt in _INIT_SQLS:
                try:
                    await session.execute(text(stmt))
                except Exception:
                    pass  # Column/table already exists
            await session.commit()
    except Exception:
        pass
    _tables_ready = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_conversations(authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    await _ensure_tables()
    async with get_session() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id::text, COALESCE(title, query, 'New conversation') AS title, "
                    "created_at, updated_at "
                    "FROM conversations WHERE user_id = :uid "
                    "ORDER BY updated_at DESC LIMIT 50"
                ),
                {"uid": user_id},
            )
        ).fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "created_at": r[2].isoformat() if r[2] else None,
            "updated_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


@router.post("")
async def create_conversation(body: NewConversation, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    await _ensure_tables()
    convo_id = str(uuid.uuid4())
    async with get_session() as session:
        await session.execute(
            text(
                "INSERT INTO conversations (id, user_id, title) "
                "VALUES (:id::uuid, :uid, :title)"
            ),
            {"id": convo_id, "uid": user_id, "title": body.title},
        )
        await session.commit()
    return {"id": convo_id, "title": body.title}


@router.get("/{convo_id}")
async def get_conversation(convo_id: str, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    await _ensure_tables()
    async with get_session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT id::text, COALESCE(title, query, 'New conversation') AS title, "
                    "created_at FROM conversations "
                    "WHERE id::text = :cid AND user_id = :uid"
                ),
                {"cid": convo_id, "uid": user_id},
            )
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        msgs = (
            await session.execute(
                text(
                    "SELECT id, role, text, data, created_at "
                    "FROM conversation_messages WHERE conversation_id = :cid "
                    "ORDER BY created_at ASC"
                ),
                {"cid": convo_id},
            )
        ).fetchall()

    return {
        "id": row[0],
        "title": row[1],
        "created_at": row[2].isoformat() if row[2] else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text": m.text,
                "data": m.data,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.post("/{convo_id}/messages")
async def add_message(convo_id: str, body: NewMessage, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    await _ensure_tables()
    msg_id = f"m_{uuid.uuid4().hex[:12]}"
    async with get_session() as session:
        # Verify ownership
        owner = (
            await session.execute(
                text("SELECT user_id FROM conversations WHERE id::text = :cid"),
                {"cid": convo_id},
            )
        ).fetchone()
        if not owner or str(owner.user_id) != str(user_id):
            raise HTTPException(status_code=404, detail="Not found")

        await session.execute(
            text(
                "INSERT INTO conversation_messages (id, conversation_id, role, text, data) "
                "VALUES (:id, :cid, :role, :text, :data)"
            ),
            {
                "id": msg_id,
                "cid": convo_id,
                "role": body.role,
                "text": body.text,
                "data": json.dumps(body.data) if body.data else None,
            },
        )

        # Update conversation title from first user message
        if body.role == "user" and body.text:
            await session.execute(
                text(
                    "UPDATE conversations SET title = :title, updated_at = NOW() "
                    "WHERE id::text = :cid AND title = 'New conversation'"
                ),
                {"title": (body.text or "")[:60], "cid": convo_id},
            )
        else:
            await session.execute(
                text("UPDATE conversations SET updated_at = NOW() WHERE id::text = :cid"),
                {"cid": convo_id},
            )

        await session.commit()
    return {"id": msg_id, "role": body.role}


@router.delete("/{convo_id}")
async def delete_conversation(convo_id: str, authorization: str = Header(None)):
    user_id = _get_user_id(authorization)
    await _ensure_tables()
    async with get_session() as session:
        result = await session.execute(
            text("DELETE FROM conversations WHERE id::text = :cid AND user_id = :uid"),
            {"cid": convo_id, "uid": user_id},
        )
        await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}
