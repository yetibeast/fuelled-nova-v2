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


def _seed_fuelled_listings() -> list[dict]:
    """Create 6 fuelled listings spanning all 4 data-completeness tiers."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    base = {
        "source": "fuelled",
        "is_active": True,
        "hours": None,
        "horsepower": None,
        "fair_value": None,
        "first_seen": thirty_days_ago,
        "last_seen": now,
    }
    return [
        # Tier 1 (make+model+year) — priced
        {**base, "id": "fu-t1-priced", "title": "2018 Ariel JGK/4 Compressor",
         "category": "compressors", "make": "Ariel", "model": "JGK/4",
         "year": 2018, "condition": "Good", "asking_price": 450000,
         "url": "https://fuelled.com/listing/1"},
        # Tier 1 (make+model+year) — unpriced
        {**base, "id": "fu-t1-unpriced", "title": "2020 Caterpillar 3512 Generator",
         "category": "generators", "make": "Caterpillar", "model": "3512",
         "year": 2020, "condition": "Excellent", "asking_price": None,
         "url": "https://fuelled.com/listing/2"},
        # Tier 2 (make+year, no model) — unpriced
        {**base, "id": "fu-t2-a", "title": "2016 Waukesha Engine",
         "category": "engines", "make": "Waukesha", "model": None,
         "year": 2016, "condition": "Fair", "asking_price": None,
         "url": "https://fuelled.com/listing/3"},
        # Tier 2 (make+year, no model) — unpriced
        {**base, "id": "fu-t2-b", "title": "2019 Dresser-Rand Compressor",
         "category": "compressors", "make": "Dresser-Rand", "model": None,
         "year": 2019, "condition": "Good", "asking_price": None,
         "url": "https://fuelled.com/listing/4"},
        # Tier 3 (make only) — unpriced
        {**base, "id": "fu-t3", "title": "Sullair Compressor Package",
         "category": "compressors", "make": "Sullair", "model": None,
         "year": None, "condition": "Fair", "asking_price": None,
         "url": "https://fuelled.com/listing/5"},
        # Tier 4 (no make) — unpriced
        {**base, "id": "fu-t4", "title": "Production Separator 48x10",
         "category": "separators", "make": None, "model": None,
         "year": None, "condition": "Poor", "asking_price": None,
         "url": "https://fuelled.com/listing/6"},
    ]


def _seed_competitor_listings() -> list[dict]:
    """Create competitor listings for stale-inventory and acquisition tests."""
    now = datetime.now(timezone.utc)
    stale_400 = now - timedelta(days=400)
    stale_390 = now - timedelta(days=390)
    stale_450 = now - timedelta(days=450)
    recent_10 = now - timedelta(days=10)
    recent_45 = now - timedelta(days=45)
    recent_60 = now - timedelta(days=60)
    recent_75 = now - timedelta(days=75)

    return [
        {
            "id": "cmp-stale-dealer",
            "source": "machinio",
            "title": "2018 Ariel JGK/4 Compressor Package",
            "category": "compressors",
            "category_normalized": "compressors",
            "make": "Ariel",
            "model": "JGK/4",
            "year": 2018,
            "condition": "Good",
            "hours": 12000,
            "horsepower": 540,
            "asking_price": 425000,
            "location": "Alberta",
            "url": "https://machinio.example/listing/1",
            "first_seen": stale_400,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-stale-auction",
            "source": "ironplanet",
            "title": "2017 Ariel JGK/4 Compressor Package",
            "category": "compressors",
            "category_normalized": "compressors",
            "make": "Ariel",
            "model": "JGK/4",
            "year": 2017,
            "condition": "Good",
            "hours": 14000,
            "horsepower": 540,
            "asking_price": 390000,
            "location": "Texas",
            "url": "https://ironplanet.example/listing/2",
            "first_seen": stale_390,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-recent-dealer",
            "source": "surplusrecord",
            "title": "2019 Ariel KBZ/6 Compressor Package",
            "category": "compressors",
            "category_normalized": "compressors",
            "make": "Ariel",
            "model": "KBZ/6",
            "year": 2019,
            "condition": "Good",
            "hours": 9000,
            "horsepower": 600,
            "asking_price": 360000,
            "location": "Colorado",
            "url": "https://surplusrecord.example/listing/3",
            "first_seen": recent_10,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-peer-1",
            "source": "machinio",
            "title": "2016 Ariel JGK/4 Compressor",
            "category": "compressors",
            "category_normalized": "compressors",
            "asking_price": 330000,
            "location": "Alberta",
            "url": "https://machinio.example/listing/4",
            "first_seen": recent_45,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-peer-2",
            "source": "machinio",
            "title": "2017 Ariel JGK/4 Compressor",
            "category": "compressors",
            "category_normalized": "compressors",
            "asking_price": 340000,
            "location": "Saskatchewan",
            "url": "https://machinio.example/listing/5",
            "first_seen": recent_60,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-peer-3",
            "source": "surplusrecord",
            "title": "2018 Ariel JGK/4 Compressor",
            "category": "compressors",
            "category_normalized": "compressors",
            "asking_price": 355000,
            "location": "Oklahoma",
            "url": "https://surplusrecord.example/listing/6",
            "first_seen": recent_75,
            "last_seen": now,
            "is_active": True,
        },
        {
            "id": "cmp-peer-4",
            "source": "machinio",
            "title": "2015 Ariel JGK/4 Compressor",
            "category": "compressors",
            "category_normalized": "compressors",
            "asking_price": 365000,
            "location": "North Dakota",
            "url": "https://machinio.example/listing/7",
            "first_seen": recent_60,
            "last_seen": now,
            "is_active": True,
        },
        {
            # AllSurplus-style auction row: no asking_price, only current_bid.
            # Before the COALESCE(asking_price, current_bid) fix this row was
            # silently dropped despite having a seller_name we'd want to surface.
            "id": "cmp-stale-bid-only",
            "source": "allsurplus",
            "title": "2016 Ariel JGK/4 Compressor (Auction)",
            "category": "compressors",
            "category_normalized": "compressors",
            "make": "Ariel",
            "model": "JGK/4",
            "year": 2016,
            "condition": "Good",
            "hours": 13500,
            "horsepower": 540,
            "asking_price": None,
            "current_bid": 285000,
            "location": "Texas",
            "url": "https://allsurplus.example/listing/9",
            "first_seen": stale_400,
            "last_seen": now,
            "seller_name": "Bid-Only Test Seller",
            "seller_account_type": "Commercial",
            "is_active": True,
        },
        {
            "id": "fu-stale-ignored",
            "source": "fuelled",
            "title": "2014 Fuelled Legacy Compressor",
            "category": "compressors",
            "category_normalized": "compressors",
            "asking_price": 500000,
            "location": "Alberta",
            "url": "https://fuelled.com/listing/stale",
            "first_seen": stale_450,
            "last_seen": now,
            "is_active": False,
        },
    ]


class _InMemoryDB:
    """Simple in-memory storage that mimics the tables used by conversations and evidence."""

    def __init__(self):
        self.conversations: dict[str, dict] = {}
        self.messages: dict[str, dict] = {}
        self.evidence: dict[str, dict] = {}
        self.scrape_targets: dict[str, dict] = {}
        self.scrape_runs: dict[str, dict] = {}
        self.competitive_acquisition_targets: dict[str, dict] = {}
        self.competitive_acquisition_events: dict[str, dict] = {}
        self.listings: list[dict] = _seed_fuelled_listings() + _seed_competitor_listings()
        # Intel vertical (recurring enrichment pipeline).
        self.seller_contact_enrichment: list[dict] = []
        self.buyer_targets: list[dict] = []
        self.enrichment_runs: list[dict] = []


_db = _InMemoryDB()


class MockRow:
    """A row object whose attributes are accessible by name or by index."""

    def __init__(self, data: dict):
        self._data = data
        self._values = list(data.values())
        for k, v in data.items():
            if isinstance(k, str):
                setattr(self, k, v)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._values[idx]
        return self._data[idx]


class MockResult:
    """Mock for SQLAlchemy execute() result."""

    def __init__(self, rows: list[dict] | None = None, rowcount: int = 0):
        self._rows = [MockRow(r) for r in (rows or [])]
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        row = self.fetchone()
        if row is None:
            return None
        # Return first attribute value
        data = row._data
        if data:
            return next(iter(data.values()))
        return None


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

        # ── Intel: enrichment_queue view ────────────────────────────
        if "FROM enrichment_queue" in sql:
            now_q = datetime.now(timezone.utc)
            ninety_days_ago = now_q - timedelta(days=90)
            # Group listings by (seller_name, source).
            groups: dict[tuple, dict] = {}
            for l in self._db.listings:
                seller = l.get("seller_name")
                if not seller:
                    continue
                src = l.get("source")
                key = (seller, src)
                g = groups.setdefault(key, {"listing_volume": 0, "last_seen": None})
                g["listing_volume"] += 1
                ls = l.get("last_seen")
                if ls and (g["last_seen"] is None or ls > g["last_seen"]):
                    g["last_seen"] = ls
            # Aggregate existing enrichment per (seller, source).
            existing: dict[tuple, dict] = {}
            for e in self._db.seller_contact_enrichment:
                key = (e.get("seller_name"), e.get("source"))
                cur = existing.setdefault(key, {"last_researched_at": None, "attempts": 0})
                lr = e.get("last_researched_at")
                if lr and (cur["last_researched_at"] is None or lr > cur["last_researched_at"]):
                    cur["last_researched_at"] = lr
                if (e.get("research_attempts") or 0) > cur["attempts"]:
                    cur["attempts"] = e.get("research_attempts") or 0
            rows: list[dict] = []
            for (seller, src), g in groups.items():
                # Match e on seller; source matches either equal or NULL.
                match = existing.get((seller, src))
                if match is None:
                    match = existing.get((seller, None))
                last_researched = match["last_researched_at"] if match else None
                attempts = match["attempts"] if match else 0
                # Filter: never OR stale, attempts < 3.
                if last_researched is not None and last_researched >= ninety_days_ago:
                    continue
                if attempts >= 3:
                    continue
                if last_researched is None:
                    freshness = "never"
                elif last_researched < ninety_days_ago:
                    freshness = "stale"
                else:
                    freshness = "fresh"
                rows.append({
                    "seller_name": seller,
                    "source": src,
                    "listing_volume": g["listing_volume"],
                    "last_seen": g["last_seen"],
                    "last_researched_at": last_researched,
                    "attempts": attempts,
                    "freshness": freshness,
                })
            rows.sort(key=lambda r: -r["listing_volume"])
            lim = params.get("lim") if isinstance(params, dict) else None
            if lim:
                rows = rows[:lim]
            return MockResult(rows)

        # ── Intel: sample-listing-urls lookup ───────────────────────
        if "SELECT url FROM listings" in sql and "seller_name = :seller" in sql:
            seller = params.get("seller")
            src = params.get("source")
            urls = [
                l.get("url") for l in self._db.listings
                if l.get("seller_name") == seller and l.get("source") == src
                and l.get("url")
            ]
            return MockResult([{"url": u, 0: u} for u in urls[:3]])

        # ── Intel: enrichment_runs INSERT ───────────────────────────
        if "INSERT INTO enrichment_runs" in sql:
            row = {
                "run_id": params.get("rid", str(uuid.uuid4())),
                "started_at": datetime.now(timezone.utc),
                "finished_at": None,
                "trigger": params.get("trig", "manual"),
                "provider_chain": params.get("chain", ""),
                "sellers_total": 0,
                "sellers_succeeded": 0,
                "sellers_failed": 0,
                "contacts_added": 0,
                "cost_usd": 0.0,
                "notes": None,
            }
            self._db.enrichment_runs.append(row)
            return MockResult(rowcount=1)

        # ── Intel: enrichment_runs UPDATE (finalize) ────────────────
        if "UPDATE enrichment_runs" in sql:
            rid = params.get("rid")
            for r in self._db.enrichment_runs:
                if r["run_id"] == rid:
                    r["finished_at"] = datetime.now(timezone.utc)
                    r["sellers_total"] = params.get("total", 0)
                    r["sellers_succeeded"] = params.get("ok", 0)
                    r["sellers_failed"] = params.get("fail", 0)
                    r["contacts_added"] = params.get("added", 0)
                    r["cost_usd"] = float(params.get("cost", 0.0) or 0.0)
                    r["notes"] = params.get("notes")
                    return MockResult(rowcount=1)
            return MockResult()

        # ── Intel: seller_contact_enrichment INSERT … ON CONFLICT … ─
        # Two variants: full UPSERT_CONTACT and MARK_FAILURE.
        if "INSERT INTO seller_contact_enrichment" in sql and "ON CONFLICT" in sql:
            seller = params.get("seller")
            src = params.get("source")
            email = params.get("email")
            # Match the unique key (seller, source, email).
            existing = next(
                (e for e in self._db.seller_contact_enrichment
                 if e.get("seller_name") == seller
                 and e.get("source") == src
                 and e.get("contact_email") == email),
                None,
            )
            now_e = datetime.now(timezone.utc)
            if existing is not None:
                # ON CONFLICT DO UPDATE path.
                if "last_research_error = :error" in sql:
                    # MARK_FAILURE: bump attempts + record error
                    existing["last_researched_at"] = now_e
                    existing["research_attempts"] = (existing.get("research_attempts") or 0) + 1
                    existing["last_research_error"] = params.get("error")
                else:
                    # UPSERT_CONTACT: refresh contact fields + bump attempts
                    existing["contact_name"] = params.get("name")
                    existing["contact_title"] = params.get("title")
                    existing["contact_phone"] = params.get("phone")
                    existing["contact_linkedin"] = params.get("linkedin")
                    existing["contact_confidence"] = params.get("confidence")
                    existing["confidence_overall"] = params.get("confidence")
                    existing["location"] = params.get("location")
                    existing["outreach_notes"] = params.get("notes")
                    existing["last_researched_at"] = now_e
                    existing["research_attempts"] = (existing.get("research_attempts") or 0) + 1
                    existing["last_research_error"] = None
                return MockResult(rowcount=1)
            # INSERT path.
            row = {
                "id": str(uuid.uuid4()),
                "seller_name": seller,
                "source": src,
                "contact_name": params.get("name"),
                "contact_title": params.get("title"),
                "contact_email": email,
                "contact_phone": params.get("phone"),
                "contact_linkedin": params.get("linkedin"),
                "contact_confidence": params.get("confidence"),
                "confidence_overall": params.get("confidence"),
                "location": params.get("location"),
                "outreach_notes": params.get("notes"),
                "enrichment_source": params.get("enrichment_source"),
                "last_researched_at": now_e,
                "research_attempts": 1,
                "last_research_error": params.get("error"),
                "imported_at": now_e,
            }
            self._db.seller_contact_enrichment.append(row)
            return MockResult(rowcount=1)

        # ── Intel: status-endpoint count/sum aggregates ─────────────
        if "FROM seller_contact_enrichment" in sql and "COUNT(DISTINCT seller_name)" in sql:
            distinct = {
                r["seller_name"] for r in self._db.seller_contact_enrichment
                if r.get("contact_email")
            }
            return MockResult([{0: len(distinct)}])

        if "FROM seller_contact_enrichment" in sql and "COUNT(*)" in sql and "contact_email IS NOT NULL" in sql:
            n = sum(1 for r in self._db.seller_contact_enrichment if r.get("contact_email"))
            return MockResult([{0: n}])

        if "FROM enrichment_runs" in sql and "SUM(cost_usd)" in sql:
            total = sum(float(r.get("cost_usd") or 0) for r in self._db.enrichment_runs)
            return MockResult([{0: total}])

        # ── Intel: enrichment_runs read for status endpoint ─────────
        if "FROM enrichment_runs" in sql and "SELECT" in sql.upper():
            rows = sorted(
                self._db.enrichment_runs,
                key=lambda r: r["started_at"],
                reverse=True,
            )
            lim = params.get("lim") if isinstance(params, dict) else None
            if lim:
                rows = rows[:lim]
            return MockResult(rows)


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

        # ── Scraper Targets ─────────────────────────────────────

        # SELECT COUNT(*) FROM scrape_targets (seed check)
        if "SELECT COUNT(*) FROM scrape_targets" in sql:
            return MockResult([{"count": len(self._db.scrape_targets)}])

        # INSERT INTO scrape_targets ... VALUES ... (seed — bulk)
        if "INSERT INTO scrape_targets" in sql and "ON CONFLICT" in sql:
            # Seed data — parse is complex, just skip for mock (tables start empty)
            return MockResult()

        # INSERT INTO scrape_targets (single create via RETURNING)
        if "INSERT INTO scrape_targets" in sql and "RETURNING" in sql:
            tid = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            row = {
                "id": tid,
                "name": params.get("name", ""),
                "url": params.get("url"),
                "scraper_type": params.get("type", "scrapekit"),
                "schedule_cron": params.get("cron"),
                "status": "active",
                "last_run_at": None,
                "next_run_at": None,
                "run_requested_at": None,
                "health_pct": 100,
                "total_items": 0,
                "items_with_price": 0,
                "created_at": now,
            }
            self._db.scrape_targets[tid] = row
            return MockResult([{
                0: tid, 1: row["name"], 2: row["url"],
                3: row["scraper_type"], 4: row["schedule_cron"],
                5: row["status"], 6: now,
            }])

        # SELECT ... FROM scrape_targets ORDER BY name (list all)
        if "FROM scrape_targets" in sql and "ORDER BY name" in sql:
            rows = []
            for t in sorted(self._db.scrape_targets.values(), key=lambda x: x["name"]):
                rows.append({
                    0: t["id"], 1: t["name"], 2: t["url"], 3: t["status"],
                    4: t["scraper_type"], 5: t["schedule_cron"], 6: t["last_run_at"],
                    7: t["next_run_at"], 8: t["run_requested_at"], 9: t["health_pct"],
                    10: t["total_items"], 11: t["items_with_price"], 12: t["created_at"],
                })
            return MockResult(rows)

        # UPDATE scrape_targets SET run_requested_at ... WHERE name = 'sold_price_harvester'
        if "UPDATE scrape_targets SET run_requested_at" in sql and "sold_price_harvester" in sql:
            for t in self._db.scrape_targets.values():
                if t["name"] == "sold_price_harvester":
                    t["run_requested_at"] = datetime.now(timezone.utc)
                    return MockResult([{0: t["id"]}], rowcount=1)
            return MockResult()

        # UPDATE scrape_targets SET run_requested_at = NOW() WHERE id = :tid (trigger run)
        if "UPDATE scrape_targets SET run_requested_at" in sql and "RETURNING name" in sql:
            tid = params.get("tid", "")
            t = self._db.scrape_targets.get(tid)
            if t:
                t["run_requested_at"] = datetime.now(timezone.utc)
                return MockResult([{0: t["name"]}], rowcount=1)
            return MockResult()

        # UPDATE scrape_targets SET status = 'paused'
        if "UPDATE scrape_targets SET status = 'paused'" in sql:
            tid = params.get("tid", "")
            t = self._db.scrape_targets.get(tid)
            if t:
                t["status"] = "paused"
                return MockResult(rowcount=1)
            return MockResult()

        # UPDATE scrape_targets SET status = 'active'
        if "UPDATE scrape_targets SET status = 'active'" in sql:
            tid = params.get("tid", "")
            t = self._db.scrape_targets.get(tid)
            if t:
                t["status"] = "active"
                return MockResult(rowcount=1)
            return MockResult()

        # UPDATE scrape_targets SET ... WHERE id = :tid (generic update)
        if "UPDATE scrape_targets SET" in sql and "id = :tid" in sql:
            tid = params.get("tid", "")
            t = self._db.scrape_targets.get(tid)
            if t:
                for k in ("name", "url", "scraper_type", "schedule_cron", "status"):
                    if k in params:
                        t[k] = params[k]
                return MockResult(rowcount=1)
            return MockResult()

        # DELETE FROM scrape_runs WHERE target_id
        if "DELETE FROM scrape_runs WHERE target_id" in sql:
            tid = params.get("tid", "")
            to_del = [k for k, v in self._db.scrape_runs.items() if v["target_id"] == tid]
            for k in to_del:
                del self._db.scrape_runs[k]
            return MockResult(rowcount=len(to_del))

        # DELETE FROM scrape_targets WHERE id
        if "DELETE FROM scrape_targets WHERE id" in sql:
            tid = params.get("tid", "")
            if tid in self._db.scrape_targets:
                del self._db.scrape_targets[tid]
                return MockResult(rowcount=1)
            return MockResult()

        # SELECT ... FROM scrape_runs ... ORDER BY ... target_id (DISTINCT ON)
        if "DISTINCT ON (target_id)" in sql:
            # Latest run per target
            latest: dict[str, dict] = {}
            for r in self._db.scrape_runs.values():
                tid = r["target_id"]
                if tid not in latest or r["started_at"] > latest[tid]["started_at"]:
                    latest[tid] = r
            rows = []
            for r in latest.values():
                rows.append({
                    0: r["target_id"], 1: r["status"], 2: r["started_at"],
                    3: r.get("completed_at"), 4: r["items_found"],
                    5: r["items_new"], 6: r.get("items_updated", 0),
                    7: r.get("error_message"), 8: r.get("duration_ms"),
                })
            return MockResult(rows)

        # SELECT ... FROM scrape_runs WHERE target_id = :tid ORDER BY started_at DESC LIMIT 20
        if "FROM scrape_runs" in sql and "target_id = :tid" in sql:
            tid = params.get("tid", "")
            rows = [r for r in self._db.scrape_runs.values() if r["target_id"] == tid]
            rows.sort(key=lambda x: x["started_at"], reverse=True)
            result_rows = []
            for r in rows[:20]:
                result_rows.append({
                    0: r["id"], 1: r["target_id"], 2: r["site_name"],
                    3: r["started_at"], 4: r.get("completed_at"),
                    5: r["status"], 6: r["items_found"], 7: r["items_new"],
                    8: r.get("items_updated", 0), 9: r.get("final_prices_harvested", 0),
                    10: r.get("error_message"), 11: r.get("duration_ms"),
                })
            return MockResult(result_rows)

        # SELECT ... FROM scrape_runs sr ORDER BY sr.started_at DESC LIMIT 20 (recent all)
        if "FROM scrape_runs" in sql and "ORDER BY" in sql and "LIMIT 20" in sql:
            rows = list(self._db.scrape_runs.values())
            rows.sort(key=lambda x: x["started_at"], reverse=True)
            result_rows = []
            for r in rows[:20]:
                result_rows.append({
                    0: r["id"], 1: r["target_id"], 2: r["site_name"],
                    3: r["started_at"], 4: r.get("completed_at"),
                    5: r["status"], 6: r["items_found"], 7: r["items_new"],
                    8: r.get("items_updated", 0), 9: r.get("final_prices_harvested", 0),
                    10: r.get("error_message"), 11: r.get("duration_ms"),
                })
            return MockResult(result_rows)

        # Supply-targets aggregate (must precede the generic GROUP BY source matcher).
        # No seeded listings have seller_source_id, so the response is an empty list.
        if "seller_key" in sql and ("consignment_count" in sql or "event_count" in sql):
            return MockResult([])

        # Supply-targets drilldown — SELECT listing rows for one (source, seller_source_id)
        if "FROM listings" in sql and "seller_source_id = :sid" in sql:
            return MockResult([])

        # ── Mailout buyers export (no listings join) ──
        # GET /api/admin/mailout/buyers.csv — SELECT from buyer_targets.
        if "FROM buyer_targets" in sql and "SELECT" in sql.upper():
            buyer_rows = getattr(self._db, "buyer_targets", [])
            vertical_filter = params.get("vertical")
            limit_b = params.get("limit", 5000) or 5000
            filtered = [
                b for b in buyer_rows
                if (vertical_filter is None or b.get("vertical") == vertical_filter)
            ]
            filtered.sort(key=lambda b: (
                b.get("vertical") or "￿",  # NULLS LAST
                b.get("company") or "",
                b.get("contact_name") or "￿",
            ))
            out_rows = []
            for b in filtered[:limit_b]:
                out_rows.append({
                    0: b.get("vertical"),
                    1: b.get("company"),
                    2: b.get("ticker"),
                    3: b.get("hq"),
                    4: b.get("basin"),
                    5: b.get("scale"),
                    6: b.get("capex_driver"),
                    7: b.get("suppliers_page"),
                    8: b.get("contact_name"),
                    9: b.get("contact_title"),
                    10: b.get("contact_email"),
                    11: b.get("contact_linkedin"),
                    12: b.get("contact_confidence"),
                    13: b.get("location"),
                    14: b.get("outreach_notes"),
                })
            return MockResult(out_rows)

        # ── Mailout sellers aggregation (must precede generic GROUP BY source) ──
        # GET /api/admin/mailout/sellers.csv — CTE-wrapped GROUP BY (source, seller_name)
        # plus LEFT JOIN seller_contact_enrichment for the enriched_* columns.
        if "seller_contact_enrichment" in sql and "FROM listings" in sql:
            now_m = datetime.now(timezone.utc)
            src_filter = params.get("source")
            acct_filter = params.get("account_type")
            min_active = params.get("min_active", 0) or 0
            limit_m = params.get("limit", 5000) or 5000

            groups: dict[tuple, list[dict]] = {}
            for l in self._db.listings:
                seller = l.get("seller_name")
                if not seller:
                    continue
                source_val = l.get("source")
                if src_filter and source_val != src_filter:
                    continue
                if acct_filter and l.get("seller_account_type") != acct_filter:
                    continue
                groups.setdefault((source_val, seller), []).append(l)

            mailout_rows = []
            for (src, seller), items in groups.items():
                active_30d = sum(
                    1 for l in items
                    if l.get("last_seen") and l["last_seen"] >= now_m - timedelta(days=30)
                )
                if active_30d < min_active:
                    continue
                first_seen_vals = [l["first_seen"] for l in items if l.get("first_seen")]
                last_seen_vals = [l["last_seen"] for l in items if l.get("last_seen")]
                cats = sorted({l.get("category_normalized") for l in items if l.get("category_normalized")})
                ask_total = sum(
                    (l.get("asking_price") or l.get("current_bid") or 0) for l in items
                )

                def _first_nonnull(field: str, _items=items):
                    for l in _items:
                        v = l.get(field)
                        if v:
                            return v
                    return None

                # LEFT JOIN seller_contact_enrichment: rows match when
                #   e.seller_name == seller AND (e.source IS NULL OR e.source == src)
                enrich_rows = getattr(self._db, "seller_contact_enrichment", [])
                matches = [
                    e for e in enrich_rows
                    if e.get("seller_name") == seller
                    and (e.get("source") is None or e.get("source") == src)
                ]

                def _max_e(field: str, _matches=matches):
                    vals = [m.get(field) for m in _matches if m.get(field)]
                    return max(vals) if vals else None

                mailout_rows.append({
                    0: src,
                    1: seller,
                    2: _first_nonnull("seller_account_type"),
                    3: len(items),
                    4: active_30d,
                    5: min(first_seen_vals).date() if first_seen_vals else None,
                    6: max(last_seen_vals).date() if last_seen_vals else None,
                    7: ", ".join(cats) if cats else None,
                    8: int(ask_total),
                    9: _first_nonnull("event_contact_name"),
                    10: _first_nonnull("event_contact_email"),
                    11: _first_nonnull("event_contact_phone"),
                    12: _first_nonnull("seller_other_assets_url"),
                    13: _first_nonnull("url"),
                    14: _max_e("contact_name"),
                    15: _max_e("contact_title"),
                    16: _max_e("contact_email"),
                    17: _max_e("contact_confidence"),
                    18: _max_e("contact_linkedin"),
                    19: _max_e("outreach_notes"),
                })
            mailout_rows.sort(key=lambda r: (-r[3], r[0] or "", r[1] or ""))
            return MockResult(mailout_rows[:limit_m])

        # SELECT source, COUNT(*) ... FROM listings GROUP BY source (listing counts)
        if "FROM listings" in sql and "GROUP BY source" in sql and "asking_price" in sql:
            counts: dict[str, dict] = {}
            for l in self._db.listings:
                src = l.get("source", "")
                if src not in counts:
                    counts[src] = {"total": 0, "with_price": 0}
                counts[src]["total"] += 1
                if l.get("asking_price", 0) > 0:
                    counts[src]["with_price"] += 1
            rows = [{0: k, 1: v["total"], 2: v["with_price"]} for k, v in counts.items()]
            return MockResult(rows)

        # Harvest stats: FILTER (WHERE auction_end ...)
        if "FILTER" in sql and "auction_end" in sql:
            now = datetime.now(timezone.utc)
            total_closed = sum(1 for l in self._db.listings if l.get("auction_end") and l["auction_end"] < now)
            harvested = sum(1 for l in self._db.listings if l.get("auction_end") and l["auction_end"] < now and l.get("final_price") is not None)
            remaining = total_closed - harvested
            return MockResult([{0: total_closed, 1: harvested, 2: remaining}])

        # Harvest breakdown by source
        if "FROM listings" in sql and "auction_end" in sql and "final_price IS NULL" in sql and "GROUP BY source" in sql:
            now = datetime.now(timezone.utc)
            counts_by_src: dict[str, int] = {}
            for l in self._db.listings:
                if l.get("auction_end") and l["auction_end"] < now and l.get("final_price") is None:
                    src = l.get("source", "")
                    counts_by_src[src] = counts_by_src.get(src, 0) + 1
            rows = [{0: k, 1: v} for k, v in sorted(counts_by_src.items(), key=lambda x: -x[1])]
            return MockResult(rows)

        # ── Competitive stale inventory / acquisition ─────────────

        if "SELECT COUNT(*) FROM listings WHERE LOWER(source) != 'fuelled'" in sql:
            count = sum(1 for l in self._db.listings if str(l.get("source", "")).lower() != "fuelled")
            return MockResult([{0: count}])

        if "COUNT(*)" in sql and "first_seen >= NOW() - INTERVAL '7 days'" in sql and "LOWER(source) != 'fuelled'" in sql:
            now = datetime.now(timezone.utc)
            count = sum(
                1 for l in self._db.listings
                if str(l.get("source", "")).lower() != "fuelled"
                and l.get("first_seen")
                and l["first_seen"] >= now - timedelta(days=7)
            )
            return MockResult([{0: count}])

        if "COUNT(*)" in sql and "first_seen < NOW() - INTERVAL '60 days'" in sql and "COALESCE(asking_price, current_bid" in sql:
            now = datetime.now(timezone.utc)
            exclude_fuelled = "LOWER(source) != 'fuelled'" in sql
            count = 0
            for l in self._db.listings:
                if exclude_fuelled and str(l.get("source", "")).lower() == "fuelled":
                    continue
                if not l.get("first_seen") or not l.get("last_seen"):
                    continue
                if (l.get("asking_price") or l.get("current_bid") or 0) <= 0:
                    continue
                if l["first_seen"] < now - timedelta(days=60) and l["last_seen"] > now - timedelta(days=30):
                    count += 1
            return MockResult([{0: count}])

        if "EXTRACT(DAY FROM NOW() - first_seen)" in sql and "FROM listings" in sql:
            now = datetime.now(timezone.utc)
            exclude_fuelled = "LOWER(source) != 'fuelled'" in sql
            rows = []
            for l in self._db.listings:
                if exclude_fuelled and str(l.get("source", "")).lower() == "fuelled":
                    continue
                if not l.get("first_seen") or not l.get("last_seen"):
                    continue
                if (l.get("asking_price") or l.get("current_bid") or 0) <= 0:
                    continue
                if l["first_seen"] >= now - timedelta(days=60):
                    continue
                if l["last_seen"] <= now - timedelta(days=30):
                    continue
                rows.append({
                    0: l.get("title"),
                    1: l.get("source"),
                    2: l.get("asking_price") or l.get("current_bid"),
                    3: l.get("category_normalized") or l.get("category"),
                    4: l.get("location"),
                    5: l.get("url"),
                    6: l.get("first_seen"),
                    7: (now - l["first_seen"]).days,
                })
            rows.sort(key=lambda row: row[6])
            return MockResult(rows[:25])

        if "FROM listings" in sql and "LOWER(source) != 'fuelled'" in sql and "COALESCE(asking_price, current_bid" in sql and "last_seen" in sql and "first_seen" in sql and "GROUP BY" not in sql and "COUNT(*)" not in sql:
            now = datetime.now(timezone.utc)
            rows = []
            for l in self._db.listings:
                if str(l.get("source", "")).lower() == "fuelled":
                    continue
                if not l.get("first_seen") or not l.get("last_seen"):
                    continue
                if (l.get("asking_price") or l.get("current_bid") or 0) <= 0:
                    continue
                rows.append({
                    "id": l.get("id"),
                    "title": l.get("title"),
                    "source": l.get("source"),
                    "asking_price": l.get("asking_price"),
                    "current_bid": l.get("current_bid"),
                    "category": l.get("category"),
                    "category_normalized": l.get("category_normalized") or l.get("category"),
                    "make": l.get("make"),
                    "model": l.get("model"),
                    "year": l.get("year"),
                    "condition": l.get("condition"),
                    "hours": l.get("hours"),
                    "horsepower": l.get("horsepower"),
                    "location": l.get("location"),
                    "url": l.get("url"),
                    "first_seen": l.get("first_seen"),
                    "last_seen": l.get("last_seen"),
                    "seller_name": l.get("seller_name"),
                    "seller_account_type": l.get("seller_account_type"),
                    "seller_other_assets_url": l.get("seller_other_assets_url"),
                    "event_contact_name": l.get("event_contact_name"),
                    "event_contact_email": l.get("event_contact_email"),
                    "event_contact_phone": l.get("event_contact_phone"),
                    "days_listed": (now - l["first_seen"]).days,
                })
            return MockResult(rows)

        if "SELECT * FROM competitive_acquisition_targets" in sql and "source_listing_id = :source_listing_id" in sql:
            source_listing_id = params.get("source_listing_id")
            row = next(
                (r for r in self._db.competitive_acquisition_targets.values() if r["source_listing_id"] == source_listing_id),
                None,
            )
            return MockResult([row] if row else [])

        if "SELECT * FROM competitive_acquisition_targets" in sql and "id = :target_id" in sql:
            row = self._db.competitive_acquisition_targets.get(params.get("target_id", ""))
            return MockResult([row] if row else [])

        if "SELECT * FROM competitive_acquisition_targets" in sql:
            rows = sorted(
                self._db.competitive_acquisition_targets.values(),
                key=lambda row: row["updated_at"],
                reverse=True,
            )
            status = params.get("status")
            if status:
                rows = [row for row in rows if row.get("status") == status]
            return MockResult(rows)

        if "INSERT INTO competitive_acquisition_targets" in sql:
            row = dict(params)
            self._db.competitive_acquisition_targets[row["id"]] = row
            return MockResult(rowcount=1)

        if "UPDATE competitive_acquisition_targets SET status = :status" in sql:
            row = self._db.competitive_acquisition_targets.get(params.get("target_id", ""))
            if not row:
                return MockResult(rowcount=0)
            row["status"] = params.get("status")
            row["assigned_to"] = params.get("assigned_to")
            row["notes"] = params.get("notes")
            row["updated_at"] = params.get("updated_at")
            return MockResult(rowcount=1)

        if "UPDATE competitive_acquisition_targets SET draft_payload = :draft_payload" in sql:
            row = self._db.competitive_acquisition_targets.get(params.get("target_id", ""))
            if not row:
                return MockResult(rowcount=0)
            row["draft_payload"] = params.get("draft_payload")
            row["updated_at"] = params.get("updated_at")
            return MockResult(rowcount=1)

        if "SELECT status, COUNT(*) AS cnt FROM competitive_acquisition_targets GROUP BY status" in sql:
            counts: dict[str, int] = {}
            for row in self._db.competitive_acquisition_targets.values():
                status = row.get("status", "new")
                counts[status] = counts.get(status, 0) + 1
            return MockResult([{0: status, 1: count, "status": status, "cnt": count} for status, count in counts.items()])

        if "INSERT INTO competitive_acquisition_events" in sql:
            row = dict(params)
            self._db.competitive_acquisition_events[row["id"]] = row
            return MockResult(rowcount=1)

        # ── Fuelled Coverage ────────────────────────────────────────

        # INSERT INTO fuelled_valuations — no-op
        if "INSERT INTO fuelled_valuations" in sql:
            return MockResult(rowcount=1)

        # UPDATE listings SET fair_value — apply in-memory
        if "UPDATE listings SET fair_value" in sql:
            lid = params.get("lid", "")
            fv = params.get("fv")
            for l in self._db.listings:
                if l["id"] == lid:
                    l["fair_value"] = fv
                    break
            return MockResult(rowcount=1)

        # Coverage stats: source='fuelled' + COUNT(*) + AVG(
        if "source = 'fuelled'" in sql and "COUNT(*)" in sql and "AVG(" in sql:
            fl = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            total = len(fl)
            asking_ct = sum(1 for l in fl if (l.get("asking_price") or 0) > 0)
            valued_ct = sum(1 for l in fl if (l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)
            ai_only_ct = sum(1 for l in fl if (l.get("fair_value") or 0) > 0 and not ((l.get("asking_price") or 0) > 0))
            # Completeness per item
            scores = []
            for l in fl:
                s = 0
                if l.get("make"): s += 25
                if l.get("model"): s += 20
                if l.get("year"): s += 25
                if l.get("hours") is not None: s += 15
                if l.get("horsepower") is not None: s += 10
                if l.get("condition"): s += 5
                scores.append(s)
            avg_comp = round(sum(scores) / len(scores), 1) if scores else 0
            return MockResult([{0: total, 1: asking_ct, 2: valued_ct, 3: ai_only_ct, 4: avg_comp}])

        # Tier breakdown: source='fuelled' + tier + GROUP BY
        if "source = 'fuelled'" in sql and "tier" in sql and "GROUP BY" in sql:
            fl = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            # Unvalued only
            unvalued = [l for l in fl if not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            tier_counts: dict[int, int] = {}
            for l in unvalued:
                has_make = bool(l.get("make"))
                has_model = bool(l.get("model"))
                has_year = bool(l.get("year"))
                if has_make and has_model and has_year:
                    t = 1
                elif has_make and has_year:
                    t = 2
                elif has_make:
                    t = 3
                else:
                    t = 4
                tier_counts[t] = tier_counts.get(t, 0) + 1
            rows = [{"tier": t, "cnt": c} for t, c in sorted(tier_counts.items())]
            return MockResult(rows)

        # Category breakdown: source='fuelled' + category + GROUP BY + LIMIT
        if "source = 'fuelled'" in sql and "category" in sql and "GROUP BY" in sql and "LIMIT" in sql:
            fl = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            unvalued = [l for l in fl if not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            cat_counts: dict[str, int] = {}
            for l in unvalued:
                cat = l.get("category") or "unknown"
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            rows = [{"category": c, "cnt": n} for c, n in sorted(cat_counts.items(), key=lambda x: -x[1])[:10]]
            return MockResult(rows)

        # Report query: source='fuelled' + first_seen + ORDER BY — full rows for unvalued
        if "source = 'fuelled'" in sql and "first_seen" in sql and "ORDER BY" in sql:
            fl = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            unvalued = [l for l in fl if not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            rows = []
            for l in unvalued:
                rows.append({
                    "id": l["id"], "title": l.get("title"), "category": l.get("category"),
                    "make": l.get("make"), "model": l.get("model"), "year": l.get("year"),
                    "condition": l.get("condition"), "hours": l.get("hours"),
                    "horsepower": l.get("horsepower"), "url": l.get("url"),
                    "first_seen": l.get("first_seen"),
                })
            return MockResult(rows)

        # Batch query: source='fuelled' + LIMIT + id + title — items for pricing
        if "source = 'fuelled'" in sql and "LIMIT" in sql and "id" in sql and "title" in sql:
            fl = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            unvalued = [l for l in fl if not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            limit = 10
            rows = []
            for l in unvalued[:limit]:
                rows.append({
                    "id": l["id"], "title": l.get("title"), "category": l.get("category"),
                    "make": l.get("make"), "model": l.get("model"), "year": l.get("year"),
                    "condition": l.get("condition"), "hours": l.get("hours"),
                    "horsepower": l.get("horsepower"),
                })
            return MockResult(rows)

        return MockResult()

    async def commit(self):
        pass

    async def rollback(self):
        pass


@asynccontextmanager
async def _mock_get_session():
    yield MockSession(_db)


@asynccontextmanager
async def _mock_get_state_session():
    yield MockSession(_db)


@pytest.fixture(autouse=True)
def _patch_db():
    """Replace get_session with in-memory mock for DB-dependent endpoints."""
    global _db
    _db = _InMemoryDB()

    # Reset table-creation flags and module-level state
    from app.api import conversations, evidence, admin_scrapers, fuelled_coverage, competitive, competitive_queue
    conversations._tables_ready = False
    evidence._tables_ready = False
    admin_scrapers._tables_ready = False
    competitive_queue._state_tables_ready = False
    fuelled_coverage._table_init = False
    fuelled_coverage._fuelled_job = None

    with patch("app.db.session.get_session", _mock_get_session), \
         patch("app.db.state_session.get_state_session", _mock_get_state_session), \
         patch("app.api.competitive.get_session", _mock_get_session), \
         patch("app.api.competitive_queue.get_session", _mock_get_session), \
         patch("app.api.competitive_queue.get_state_session", _mock_get_state_session), \
         patch("app.api.conversations.get_session", _mock_get_session), \
         patch("app.api.evidence.get_session", _mock_get_session), \
         patch("app.api.admin_scrapers.get_session", _mock_get_session), \
         patch("app.api.admin_supply_targets.get_session", _mock_get_session), \
         patch("app.api.admin_mailout.get_session", _mock_get_session), \
         patch("app.api.fuelled_coverage.get_session", _mock_get_session), \
         patch("app.api.v2_intel.get_session", _mock_get_session):
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
