"""Shared fixtures for Phase C + D tests."""
from __future__ import annotations

import json
import re
import uuid
import jwt
import pytest
from collections import namedtuple
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import JWT_SECRET
from app.main import app


# ── Token helpers ───────────────────────────────────────────────────────────


def _make_token(user_id: str = "test-user-1", role: str = "admin", expires_hours: int = 1) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ── In-memory DB mock ──────────────────────────────────────────────────────


class _InMemoryDB:
    """Simple in-memory storage that mimics the tables used by conversations and evidence."""

    def __init__(self):
        self.conversations: dict[str, dict] = {}
        self.messages: dict[str, dict] = {}
        self.evidence: dict[str, dict] = {}


_db = _InMemoryDB()


class MockRow:
    """A row object whose attributes are accessible by name."""

    def __init__(self, data: dict):
        self._data = data
        for k, v in data.items():
            setattr(self, k, v)


class MockResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, rows: list[dict] | None = None, rowcount: int = 0):
        self._rows = [MockRow(r) for r in (rows or [])]
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class MockSession:
    """Async session mock backed by _InMemoryDB."""

    def __init__(self, db: _InMemoryDB):
        self._db = db

    async def execute(self, sql_text, params=None):
        sql = getattr(sql_text, "text", str(sql_text)).strip()
        params = params or {}

        # CREATE TABLE — no-op
        if sql.upper().startswith("CREATE TABLE") or sql.upper().startswith("CREATE INDEX"):
            return MockResult()

        # ── Conversations (order matters: DELETE/UPDATE before SELECT) ────

        # DELETE FROM conversations — must be before SELECT patterns
        if "DELETE FROM conversations" in sql:
            cid = params.get("cid", "")
            uid = params.get("uid", "")
            row = self._db.conversations.get(cid)
            if row and row["user_id"] == uid:
                del self._db.conversations[cid]
                self._db.messages = {
                    k: v for k, v in self._db.messages.items()
                    if v["conversation_id"] != cid
                }
                return MockResult(rowcount=1)
            return MockResult(rowcount=0)

        # INSERT INTO conversations
        if "INSERT INTO conversations" in sql and "conversation_messages" not in sql:
            row = {
                "id": params.get("id", ""),
                "user_id": params.get("uid", ""),
                "title": params.get("title", "New conversation"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self._db.conversations[row["id"]] = row
            return MockResult(rowcount=1)

        # INSERT INTO conversation_messages
        if "INSERT INTO conversation_messages" in sql:
            row = {
                "id": params.get("id", ""),
                "conversation_id": params.get("cid", ""),
                "role": params.get("role", ""),
                "text": params.get("text"),
                "data": json.loads(params["data"]) if params.get("data") else None,
                "created_at": datetime.now(timezone.utc),
            }
            self._db.messages[row["id"]] = row
            return MockResult(rowcount=1)

        # UPDATE conversations SET title ... WHERE ... title = 'New conversation'
        if "UPDATE conversations SET title" in sql and "New conversation" in sql:
            cid = params.get("cid", "")
            row = self._db.conversations.get(cid)
            if row and row["title"] == "New conversation":
                row["title"] = params.get("title", row["title"])
                row["updated_at"] = datetime.now(timezone.utc)
            return MockResult(rowcount=1 if row else 0)

        # UPDATE conversations SET updated_at
        if "UPDATE conversations SET updated_at" in sql:
            cid = params.get("cid", "")
            row = self._db.conversations.get(cid)
            if row:
                row["updated_at"] = datetime.now(timezone.utc)
            return MockResult(rowcount=1 if row else 0)

        # SELECT user_id FROM conversations WHERE id = :cid
        if "SELECT user_id FROM conversations" in sql:
            cid = params.get("cid", "")
            row = self._db.conversations.get(cid)
            if row:
                return MockResult([{"user_id": row["user_id"]}])
            return MockResult()

        # SELECT ... FROM conversation_messages WHERE conversation_id = :cid
        if "FROM conversation_messages" in sql:
            cid = params.get("cid", "")
            rows = [r for r in self._db.messages.values() if r["conversation_id"] == cid]
            rows.sort(key=lambda r: r["created_at"])
            return MockResult(rows)

        # SELECT ... FROM conversations WHERE id = :cid AND user_id = :uid
        if "FROM conversations" in sql and "id = :cid" in sql:
            cid = params.get("cid", "")
            uid = params.get("uid", "")
            row = self._db.conversations.get(cid)
            if row and row["user_id"] == uid:
                return MockResult([row])
            return MockResult()

        # SELECT ... FROM conversations WHERE user_id = :uid ORDER BY ...
        if "FROM conversations" in sql and "user_id = :uid" in sql:
            uid = params.get("uid", "")
            rows = [r for r in self._db.conversations.values() if r["user_id"] == uid]
            rows.sort(key=lambda r: r["updated_at"], reverse=True)
            return MockResult(rows[:50])

        # ── Evidence ─────────────────────────────────────────────

        # INSERT INTO pricing_evidence_intake
        if "INSERT INTO pricing_evidence_intake" in sql:
            row = {
                "id": params.get("id", ""),
                "manufacturer": params.get("mfr", ""),
                "model": params.get("model", ""),
                "category": params.get("cat", ""),
                "price_value": params.get("price"),
                "confidence": params.get("conf", "LOW"),
                "tools_used": params.get("tools", "[]"),
                "user_message": params.get("msg", ""),
                "structured_data": json.loads(params["data"]) if params.get("data") else {},
                "review_flag": "auto_capture",
                "comment": "",
                "user_corrected_fmv": None,
                "created_at": datetime.now(timezone.utc),
            }
            self._db.evidence[row["id"]] = row
            return MockResult(rowcount=1)

        # SELECT id FROM pricing_evidence_intake WHERE id = :id
        if "SELECT id FROM pricing_evidence_intake" in sql:
            eid = params.get("id", "")
            row = self._db.evidence.get(eid)
            if row:
                return MockResult([{"id": row["id"]}])
            return MockResult()

        # SELECT * FROM pricing_evidence_intake WHERE id = :id
        if "SELECT *" in sql and "pricing_evidence_intake" in sql and "id = :id" in sql:
            eid = params.get("id", "")
            row = self._db.evidence.get(eid)
            if row:
                return MockResult([row])
            return MockResult()

        # UPDATE pricing_evidence_intake SET review_flag = 'needs_review'
        if "UPDATE pricing_evidence_intake SET review_flag = 'needs_review'" in sql:
            eid = params.get("id", "")
            row = self._db.evidence.get(eid)
            if row:
                row["review_flag"] = "needs_review"
                row["comment"] = params.get("comment", "")
                if "correction" in params:
                    row["user_corrected_fmv"] = params["correction"]
            return MockResult(rowcount=1 if row else 0)

        # UPDATE pricing_evidence_intake SET review_flag = 'promoted'
        if "review_flag = 'promoted'" in sql:
            eid = params.get("id", "")
            row = self._db.evidence.get(eid)
            if row:
                row["review_flag"] = "promoted"
            return MockResult(rowcount=1 if row else 0)

        # SELECT ... WHERE review_flag = 'needs_review'
        if "review_flag = 'needs_review'" in sql and "SELECT" in sql.upper():
            rows = [r for r in self._db.evidence.values() if r["review_flag"] == "needs_review"]
            rows.sort(key=lambda r: r["created_at"], reverse=True)
            return MockResult(rows[:50])

        return MockResult()

    async def commit(self):
        pass


@asynccontextmanager
async def _mock_get_session():
    yield MockSession(_db)


@pytest.fixture(autouse=True)
def _patch_db():
    """Replace get_session with in-memory mock for DB-dependent endpoints."""
    global _db
    _db = _InMemoryDB()

    # Reset table-creation flags
    from app.api import conversations, evidence
    conversations._tables_ready = False
    evidence._tables_ready = False

    with patch("app.db.session.get_session", _mock_get_session), \
         patch("app.api.conversations.get_session", _mock_get_session), \
         patch("app.api.evidence.get_session", _mock_get_session):
        yield


# ── Standard fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token():
    return _make_token(role="admin")


@pytest.fixture
def user_token():
    return _make_token(user_id="test-user-2", role="user")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def expired_token():
    payload = {
        "sub": "test-expired",
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
