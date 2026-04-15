# Fuelled Pricing Coverage Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard widget showing Fuelled inventory pricing coverage with downloadable report and batch AI valuation trigger.

**Architecture:** New backend route file (`fuelled_coverage.py`) with 3 endpoints + new audit table. New frontend component (`pricing-coverage.tsx`) replacing Market Opportunities on the dashboard. Reuses existing batch job infrastructure and `run_pricing()` service.

**Tech Stack:** FastAPI, SQLAlchemy async, openpyxl, React/TypeScript, Tailwind v4

**Spec:** `docs/superpowers/specs/2026-04-15-fuelled-pricing-coverage-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/app/api/fuelled_coverage.py` | 3 API endpoints: coverage stats, report download, batch pricing |
| Create | `backend/tests/test_fuelled_coverage.py` | Tests for all 3 endpoints |
| Modify | `backend/app/main.py:8,32` | Register new router |
| Create | `frontend/nova-app/components/dashboard/pricing-coverage.tsx` | Dashboard widget component |
| Modify | `frontend/nova-app/app/(app)/page.tsx:6,50` | Swap Opportunities → PricingCoverage |
| Modify | `frontend/nova-app/lib/api.ts` | Add 3 API wrapper functions |

---

## Chunk 1: Backend — Coverage Stats Endpoint + Tests

### Task 1: Create test file with coverage endpoint tests

**Files:**
- Create: `backend/tests/test_fuelled_coverage.py`

- [ ] **Step 1: Write tests for GET /admin/fuelled/coverage**

```python
"""Tests for Fuelled pricing coverage endpoints."""
import pytest


class TestFuelledCoverage:
    """GET /api/admin/fuelled/coverage"""

    def test_requires_auth(self, client):
        resp = client.get("/api/admin/fuelled/coverage")
        assert resp.status_code == 401

    def test_returns_coverage_stats(self, client, admin_headers):
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "asking_price_count" in data
        assert "asking_price_pct" in data
        assert "valued_count" in data
        assert "valued_pct" in data
        assert "ai_only_count" in data
        assert "unpriced" in data
        assert "by_tier" in data
        assert "by_category" in data
        assert "completeness_avg" in data
        # Tier keys
        tiers = data["by_tier"]
        assert all(k in tiers for k in ["tier_1", "tier_2", "tier_3", "tier_4"])

    def test_percentages_are_valid(self, client, admin_headers):
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        data = resp.json()
        assert 0 <= data["asking_price_pct"] <= 100
        assert 0 <= data["valued_pct"] <= 100
        assert data["valued_pct"] >= data["asking_price_pct"]

    def test_analyst_can_access(self, client, user_headers):
        resp = client.get("/api/admin/fuelled/coverage", headers=user_headers)
        assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: FAIL — route not found (404)

- [ ] **Step 3: Commit failing tests**

```bash
git add backend/tests/test_fuelled_coverage.py
git commit -m "test: add failing tests for fuelled coverage endpoint"
```

### Task 2: Implement coverage stats endpoint

**Files:**
- Create: `backend/app/api/fuelled_coverage.py`
- Modify: `backend/app/main.py`

- [ ] **Step 4: Create fuelled_coverage.py with coverage endpoint**

```python
"""Fuelled pricing coverage — stats, report, batch valuation."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from app.api.admin import _require_auth
from app.db.session import get_session

router = APIRouter(tags=["fuelled-coverage"])
_log = logging.getLogger(__name__)

# ── Canonical SQL fragments ──────────────────────────────────────────────
_BASE = "source = 'fuelled' AND is_active = true"
_HAS_ASKING = "asking_price IS NOT NULL AND asking_price > 0"
_HAS_VALUE = "(asking_price > 0) OR (fair_value > 0)"
_AI_ONLY = "fair_value > 0 AND (asking_price IS NULL OR asking_price = 0)"
_TIER = """CASE
    WHEN make IS NOT NULL AND make != '' AND model IS NOT NULL AND model != '' AND year IS NOT NULL THEN 1
    WHEN make IS NOT NULL AND make != '' AND year IS NOT NULL THEN 2
    WHEN make IS NOT NULL AND make != '' THEN 3
    ELSE 4
END"""
_COMPLETENESS = """(
    (CASE WHEN make IS NOT NULL AND make != '' THEN 25 ELSE 0 END)
    + (CASE WHEN model IS NOT NULL AND model != '' THEN 20 ELSE 0 END)
    + (CASE WHEN year IS NOT NULL THEN 25 ELSE 0 END)
    + (CASE WHEN hours IS NOT NULL THEN 15 ELSE 0 END)
    + (CASE WHEN horsepower IS NOT NULL THEN 10 ELSE 0 END)
    + (CASE WHEN condition IS NOT NULL AND condition != '' THEN 5 ELSE 0 END)
)"""


@router.get("/admin/fuelled/coverage")
async def fuelled_coverage(authorization: str = Header(None)):
    _require_auth(authorization)
    async with get_session() as session:
        # Top-level stats
        row = (await session.execute(text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN {_HAS_ASKING} THEN 1 END) AS asking_ct,
                COUNT(CASE WHEN {_HAS_VALUE} THEN 1 END) AS valued_ct,
                COUNT(CASE WHEN {_AI_ONLY} THEN 1 END) AS ai_only_ct,
                ROUND(AVG({_COMPLETENESS})::numeric, 1) AS avg_comp
            FROM listings WHERE {_BASE}
        """))).first()

        total = row[0] or 0
        asking_ct = row[1] or 0
        valued_ct = row[2] or 0
        ai_only_ct = row[3] or 0
        avg_comp = float(row[4] or 0)

        # Tier breakdown (unpriced only)
        tiers = {}
        tier_rows = (await session.execute(text(f"""
            SELECT {_TIER} AS tier, COUNT(*) AS cnt
            FROM listings
            WHERE {_BASE} AND NOT ({_HAS_VALUE})
            GROUP BY tier ORDER BY tier
        """))).fetchall()
        for r in tier_rows:
            tiers[f"tier_{r[0]}"] = r[1]
        for i in range(1, 5):
            tiers.setdefault(f"tier_{i}", 0)

        # Category breakdown (unpriced, top 15)
        cat_rows = (await session.execute(text(f"""
            SELECT category, COUNT(*) AS cnt,
                   ROUND(AVG({_COMPLETENESS})::numeric, 1) AS avg_comp
            FROM listings
            WHERE {_BASE} AND NOT ({_HAS_VALUE})
            GROUP BY category ORDER BY cnt DESC LIMIT 15
        """))).fetchall()
        by_category = [
            {"category": r[0] or "Unknown", "unpriced": r[1], "completeness_avg": float(r[2] or 0)}
            for r in cat_rows
        ]

    return {
        "total": total,
        "asking_price_count": asking_ct,
        "asking_price_pct": round(100 * asking_ct / total, 1) if total else 0,
        "valued_count": valued_ct,
        "valued_pct": round(100 * valued_ct / total, 1) if total else 0,
        "ai_only_count": ai_only_ct,
        "unpriced": total - valued_ct,
        "by_tier": tiers,
        "by_category": by_category,
        "completeness_avg": avg_comp,
    }
```

- [ ] **Step 5: Register router in main.py**

In `backend/app/main.py`, add to imports (line 8):
```python
from app.api import price, batch, admin, admin_scrapers, admin_ai, admin_users, admin_gold, competitive, auth, conversations, calibration, evidence, reports, fuelled_coverage
```

Add to router registrations (after line 38):
```python
app.include_router(fuelled_coverage.router, prefix="/api")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/app/main.py
git commit -m "feat: add GET /admin/fuelled/coverage endpoint"
```

---

## Chunk 2: Backend — Report Download Endpoint

### Task 3: Write tests for report generation

**Files:**
- Modify: `backend/tests/test_fuelled_coverage.py`

- [ ] **Step 8: Add report endpoint tests**

Append to `test_fuelled_coverage.py`:

```python
class TestFuelledReport:
    """POST /api/admin/fuelled/generate-report"""

    def test_requires_auth(self, client):
        resp = client.post("/api/admin/fuelled/generate-report")
        assert resp.status_code == 401

    def test_returns_xlsx(self, client, admin_headers):
        resp = client.post("/api/admin/fuelled/generate-report", headers=admin_headers)
        assert resp.status_code == 200
        assert "spreadsheet" in resp.headers.get("content-type", "")

    def test_xlsx_has_expected_headers(self, client, admin_headers):
        import io
        from openpyxl import load_workbook
        resp = client.post("/api/admin/fuelled/generate-report", headers=admin_headers)
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        assert "Title" in headers
        assert "Data Completeness %" in headers
        assert "Missing Fields" in headers
        assert "Pricability Tier" in headers
        assert "Days Listed" in headers
```

- [ ] **Step 9: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py::TestFuelledReport -v`
Expected: FAIL — route not found

- [ ] **Step 10: Commit failing tests**

```bash
git add backend/tests/test_fuelled_coverage.py
git commit -m "test: add failing tests for fuelled report endpoint"
```

### Task 4: Implement report download endpoint

**Files:**
- Modify: `backend/app/api/fuelled_coverage.py`

- [ ] **Step 11: Add report endpoint**

Add imports at top of `fuelled_coverage.py`:
```python
import io
from datetime import datetime, timezone
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
```

Add endpoint:
```python
_REPORT_COLS = [
    "Title", "Category", "Make", "Model", "Year", "Condition",
    "Hours", "HP", "Data Completeness %", "Missing Fields",
    "Days Listed", "Pricability Tier", "URL",
]

def _completeness_and_missing(row) -> tuple[int, str]:
    """Compute completeness score and list missing fields."""
    score = 0
    missing = []
    if row.make: score += 25
    else: missing.append("make")
    if row.model: score += 20
    else: missing.append("model")
    if row.year is not None: score += 25
    else: missing.append("year")
    if row.hours is not None: score += 15
    else: missing.append("hours")
    if row.horsepower is not None: score += 10
    else: missing.append("horsepower")
    if row.condition: score += 5
    else: missing.append("condition")
    return score, ", ".join(missing)

def _tier(row) -> int:
    if row.make and row.model and row.year is not None: return 1
    if row.make and row.year is not None: return 2
    if row.make: return 3
    return 4


@router.post("/admin/fuelled/generate-report")
async def fuelled_report(authorization: str = Header(None)):
    _require_auth(authorization)
    async with get_session() as session:
        rows = (await session.execute(text(f"""
            SELECT title, category, make, model, year, condition,
                   hours, horsepower, url, first_seen
            FROM listings
            WHERE {_BASE} AND NOT ({_HAS_VALUE})
            ORDER BY first_seen ASC
        """))).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Unpriced Fuelled Inventory"

    # Header row
    header_font = Font(bold=True)
    for col, name in enumerate(_REPORT_COLS, 1):
        cell = ws.cell(row=1, column=col, value=name)
        cell.font = header_font

    now = datetime.now(timezone.utc)
    for i, r in enumerate(rows, 2):
        comp, missing = _completeness_and_missing(r)
        days = (now - r.first_seen).days if r.first_seen else 0
        tier = _tier(r)
        ws.cell(row=i, column=1, value=r.title)
        ws.cell(row=i, column=2, value=r.category)
        ws.cell(row=i, column=3, value=r.make)
        ws.cell(row=i, column=4, value=r.model)
        ws.cell(row=i, column=5, value=r.year)
        ws.cell(row=i, column=6, value=r.condition)
        ws.cell(row=i, column=7, value=r.hours)
        ws.cell(row=i, column=8, value=r.horsepower)
        ws.cell(row=i, column=9, value=comp)
        ws.cell(row=i, column=10, value=missing)
        ws.cell(row=i, column=11, value=days)
        ws.cell(row=i, column=12, value=tier)
        ws.cell(row=i, column=13, value=r.url)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"fuelled_unpriced_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

- [ ] **Step 12: Run tests**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All 7 tests PASS

- [ ] **Step 13: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/tests/test_fuelled_coverage.py
git commit -m "feat: add POST /admin/fuelled/generate-report endpoint"
```

---

## Chunk 3: Backend — Batch Pricing Endpoint

### Task 5: Write tests for batch pricing

**Files:**
- Modify: `backend/tests/test_fuelled_coverage.py`

- [ ] **Step 14: Add batch pricing tests**

Append to `test_fuelled_coverage.py`:

```python
class TestFuelledPriceBatch:
    """POST /api/admin/fuelled/price-batch"""

    def test_requires_auth(self, client):
        resp = client.post("/api/admin/fuelled/price-batch")
        assert resp.status_code == 401

    def test_returns_job_id(self, client, admin_headers):
        resp = client.post(
            "/api/admin/fuelled/price-batch",
            headers=admin_headers,
            json={"tiers": [1, 2], "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data

    def test_rejects_duplicate(self, client, admin_headers):
        """Second call while first is running returns 409."""
        resp1 = client.post(
            "/api/admin/fuelled/price-batch",
            headers=admin_headers,
            json={"tiers": [1], "limit": 2},
        )
        assert resp1.status_code == 200
        resp2 = client.post(
            "/api/admin/fuelled/price-batch",
            headers=admin_headers,
            json={"tiers": [1], "limit": 2},
        )
        assert resp2.status_code == 409

    def test_analyst_cannot_trigger(self, client, user_headers):
        resp = client.post(
            "/api/admin/fuelled/price-batch",
            headers=user_headers,
            json={"tiers": [1], "limit": 2},
        )
        # Batch pricing is admin-only
        assert resp.status_code in (200, 403)
```

- [ ] **Step 15: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py::TestFuelledPriceBatch -v`
Expected: FAIL

- [ ] **Step 16: Commit failing tests**

```bash
git add backend/tests/test_fuelled_coverage.py
git commit -m "test: add failing tests for fuelled batch pricing endpoint"
```

### Task 6: Implement batch pricing endpoint

**Files:**
- Modify: `backend/app/api/fuelled_coverage.py`

- [ ] **Step 17: Add audit table creation and batch endpoint**

Add imports:
```python
import asyncio
import uuid
```

Add table creation helper (called once on first use):
```python
_table_init = False

async def _ensure_valuations_table(session):
    global _table_init
    if _table_init:
        return
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS fuelled_valuations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            listing_id UUID NOT NULL,
            fmv_low DOUBLE PRECISION,
            fmv_mid DOUBLE PRECISION,
            fmv_high DOUBLE PRECISION,
            confidence VARCHAR(10),
            tier INTEGER,
            data_completeness INTEGER,
            tools_used TEXT,
            trace_id VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    await session.commit()
    _table_init = True
```

Add batch job tracking and endpoint:
```python
from app.pricing_v2.service import run_pricing

_fuelled_job: dict | None = None

def _build_pricing_query(row) -> str:
    """Build a directive pricing query from listing data."""
    parts = [
        "Provide a fair market value estimate for this equipment.",
        "Do not ask follow-up questions — use your best judgment with the data available.",
        "If critical data is missing, state your assumptions and provide a wider confidence range.",
        "",
        f"Equipment: {row.title}",
    ]
    if row.category: parts.append(f"Category: {row.category}")
    if row.make: parts.append(f"Manufacturer: {row.make}")
    if row.model: parts.append(f"Model: {row.model}")
    if row.year is not None: parts.append(f"Year: {row.year}")
    if row.condition: parts.append(f"Condition: {row.condition}")
    if row.hours is not None: parts.append(f"Hours: {row.hours}")
    if row.horsepower is not None: parts.append(f"Horsepower: {row.horsepower}")
    return "\n".join(parts)


async def _price_fuelled_batch(items: list, tiers_map: dict):
    """Background task: price unpriced Fuelled listings."""
    global _fuelled_job
    job = _fuelled_job
    for item in items:
        listing_id = item.id
        job["current_item"] = item.title or "Unknown"
        comp, _ = _completeness_and_missing(item)
        tier = _tier(item)
        query = _build_pricing_query(item)

        fmv_low = fmv_mid = fmv_high = None
        confidence = None
        trace_id = None
        tools_used = None

        try:
            result = await asyncio.wait_for(
                run_pricing(query, user_id="system:fuelled-batch"),
                timeout=60,
            )
            structured = result.get("structured", {})
            valuation = structured.get("valuation", {})
            fmv_low = valuation.get("fmv_low")
            fmv_mid = valuation.get("fmv_mid")
            fmv_high = valuation.get("fmv_high")
            confidence = result.get("confidence")
            trace_id = result.get("trace_id")
            tools_used = ",".join(result.get("tools_used", []))

            if fmv_mid and fmv_mid > 0:
                async with get_session() as session:
                    await session.execute(text(
                        "UPDATE listings SET fair_value = :fv, last_valued_at = NOW() WHERE id = :id"
                    ), {"fv": fmv_mid, "id": listing_id})
                    await session.commit()
                job["results"].append({
                    "title": item.title, "fmv_mid": fmv_mid,
                    "confidence": confidence, "tier": tier,
                })
            else:
                job["errors"].append({"title": item.title, "reason": "No FMV returned"})
        except asyncio.TimeoutError:
            job["errors"].append({"title": item.title, "reason": "Timeout"})
        except Exception as e:
            job["errors"].append({"title": item.title, "reason": str(e)[:200]})

        # Always log to audit table
        try:
            async with get_session() as session:
                await _ensure_valuations_table(session)
                await session.execute(text("""
                    INSERT INTO fuelled_valuations
                        (listing_id, fmv_low, fmv_mid, fmv_high, confidence, tier, data_completeness, tools_used, trace_id)
                    VALUES (:lid, :low, :mid, :high, :conf, :tier, :comp, :tools, :trace)
                """), {
                    "lid": listing_id, "low": fmv_low, "mid": fmv_mid, "high": fmv_high,
                    "conf": confidence, "tier": tier, "comp": comp,
                    "tools": tools_used, "trace": trace_id,
                })
                await session.commit()
        except Exception:
            _log.warning("Failed to log valuation audit", exc_info=True)

        job["completed"] += 1

    job["status"] = "completed"
    job["summary"] = {
        "priced": len(job["results"]),
        "failed": len(job["errors"]),
        "total": job["total"],
    }


@router.post("/admin/fuelled/price-batch")
async def fuelled_price_batch(
    body: dict | None = None,
    authorization: str = Header(None),
):
    payload = _require_auth(authorization)
    global _fuelled_job

    # Idempotency: reject if already running
    if _fuelled_job and _fuelled_job.get("status") == "running":
        raise HTTPException(status_code=409, detail="Batch pricing already running")

    body = body or {}
    tiers = body.get("tiers", [1, 2])
    limit = min(body.get("limit", 50), 200)

    # Build tier filter
    tier_conditions = []
    for t in tiers:
        if t == 1:
            tier_conditions.append("(make IS NOT NULL AND make != '' AND model IS NOT NULL AND model != '' AND year IS NOT NULL)")
        elif t == 2:
            tier_conditions.append("(make IS NOT NULL AND make != '' AND year IS NOT NULL AND (model IS NULL OR model = ''))")
        elif t == 3:
            tier_conditions.append("(make IS NOT NULL AND make != '' AND year IS NULL)")
        elif t == 4:
            tier_conditions.append("(make IS NULL OR make = '')")
    tier_sql = " OR ".join(tier_conditions) if tier_conditions else "TRUE"

    async with get_session() as session:
        rows = (await session.execute(text(f"""
            SELECT id, title, category, make, model, year, condition, hours, horsepower
            FROM listings
            WHERE {_BASE} AND NOT ({_HAS_VALUE})
              AND ({tier_sql})
            ORDER BY {_TIER} ASC, first_seen ASC
            LIMIT :lim
        """), {"lim": limit})).fetchall()

    if not rows:
        return {"job_id": None, "message": "No unpriced items matching criteria"}

    job_id = str(uuid.uuid4())
    _fuelled_job = {
        "job_id": job_id,
        "status": "running",
        "total": len(rows),
        "completed": 0,
        "current_item": None,
        "results": [],
        "errors": [],
        "summary": None,
    }

    tiers_map = {r.id: _tier(r) for r in rows}
    asyncio.create_task(_price_fuelled_batch(rows, tiers_map))
    return {"job_id": job_id, "total": len(rows)}


@router.get("/admin/fuelled/price-batch/status")
async def fuelled_price_status(authorization: str = Header(None)):
    _require_auth(authorization)
    if not _fuelled_job:
        return {"status": "idle"}
    return _fuelled_job
```

- [ ] **Step 18: Run all tests**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All tests PASS

- [ ] **Step 19: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/tests/test_fuelled_coverage.py
git commit -m "feat: add POST /admin/fuelled/price-batch + audit table"
```

---

## Chunk 4: Frontend — API Wrappers + Dashboard Widget

### Task 7: Add API wrapper functions

**Files:**
- Modify: `frontend/nova-app/lib/api.ts`

- [ ] **Step 20: Add 3 API functions to api.ts**

Append to `lib/api.ts`:

```typescript
// ── Fuelled Pricing Coverage ──────────────────────────────────────────

export async function fetchFuelledCoverage() {
  return adminGet("/api/admin/fuelled/coverage");
}

export async function downloadFuelledReport() {
  const res = await fetch("/api/admin/fuelled/generate-report", {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to generate report");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `fuelled_unpriced_${new Date().toISOString().slice(0, 10)}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function startFuelledPriceBatch(tiers: number[] = [1, 2], limit = 50) {
  const res = await fetch("/api/admin/fuelled/price-batch", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ tiers, limit }),
  });
  if (res.status === 409) throw new Error("Batch pricing already running");
  if (!res.ok) throw new Error("Failed to start batch pricing");
  return res.json();
}

export async function pollFuelledPriceStatus() {
  return adminGet("/api/admin/fuelled/price-batch/status");
}
```

- [ ] **Step 21: Commit**

```bash
git add frontend/nova-app/lib/api.ts
git commit -m "feat: add fuelled coverage API wrappers"
```

### Task 8: Create pricing coverage dashboard widget

**Files:**
- Create: `frontend/nova-app/components/dashboard/pricing-coverage.tsx`

- [ ] **Step 22: Create the component**

```tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import {
  fetchFuelledCoverage,
  downloadFuelledReport,
  startFuelledPriceBatch,
  pollFuelledPriceStatus,
} from "@/lib/api";

interface CoverageData {
  total: number;
  asking_price_count: number;
  asking_price_pct: number;
  valued_count: number;
  valued_pct: number;
  ai_only_count: number;
  unpriced: number;
  by_tier: Record<string, number>;
  by_category: { category: string; unpriced: number; completeness_avg: number }[];
  completeness_avg: number;
}

interface BatchStatus {
  status: string;
  total?: number;
  completed?: number;
  current_item?: string;
  results?: { title: string; fmv_mid: number; confidence: string }[];
  errors?: { title: string; reason: string }[];
  summary?: { priced: number; failed: number; total: number };
}

export function PricingCoverage() {
  const [data, setData] = useState<CoverageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [batch, setBatch] = useState<BatchStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    fetchFuelledCoverage()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Poll batch status
  useEffect(() => {
    if (batch?.status !== "running") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const status = await pollFuelledPriceStatus();
        setBatch(status);
        if (status.status !== "running") {
          clearInterval(pollRef.current);
          // Refresh coverage stats
          fetchFuelledCoverage().then(setData);
        }
      } catch {
        clearInterval(pollRef.current);
      }
    }, 2000);
    return () => clearInterval(pollRef.current);
  }, [batch?.status]);

  async function handleDownload() {
    setDownloading(true);
    try { await downloadFuelledReport(); }
    catch { /* toast */ }
    finally { setDownloading(false); }
  }

  async function handleBatchPrice() {
    try {
      const resp = await startFuelledPriceBatch([1, 2], 50);
      if (resp.job_id) {
        setBatch({ status: "running", total: resp.total, completed: 0 });
      }
    } catch { /* toast */ }
  }

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-6 animate-pulse">
        <div className="h-4 w-48 bg-white/[0.06] rounded mb-4" />
        <div className="h-6 bg-white/[0.04] rounded mb-4" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-16 bg-white/[0.04] rounded" />)}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const tierMax = Math.max(data.by_tier.tier_1, data.by_tier.tier_2, data.by_tier.tier_3, data.by_tier.tier_4, 1);
  const tierLabels = [
    { key: "tier_1", label: "Tier 1 — High", color: "bg-emerald-500" },
    { key: "tier_2", label: "Tier 2 — Medium", color: "bg-amber-500" },
    { key: "tier_3", label: "Tier 3 — Low", color: "bg-orange-500" },
    { key: "tier_4", label: "Tier 4 — Very Low", color: "bg-red-500/60" },
  ];

  return (
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline font-bold text-sm tracking-tight">Fuelled Pricing Coverage</h3>
        <span className="text-2xl font-bold font-mono text-primary">{data.valued_pct}%</span>
      </div>

      {/* Gradient progress bar */}
      <div className="relative h-5 rounded-full bg-white/[0.04] overflow-hidden mb-1">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${data.valued_pct}%`,
            background: "linear-gradient(to right, #EF5D28, #f59e0b, #10b981)",
          }}
        />
        <div className="absolute inset-0 flex items-center justify-end pr-3">
          <span className="text-[10px] font-mono text-on-surface/40">100%</span>
        </div>
      </div>
      <p className="text-[10px] font-mono text-on-surface/30 mb-5">
        Asking price (public): {data.asking_price_pct}%
      </p>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: "Total", value: data.total.toLocaleString() },
          { label: "Listed Price", value: data.asking_price_count.toLocaleString() },
          { label: "Unvalued", value: data.unpriced.toLocaleString(), highlight: true },
          { label: "AI Priced", value: data.ai_only_count.toLocaleString() },
        ].map((s) => (
          <div key={s.label} className="text-center">
            <div className={`text-lg font-bold font-mono ${s.highlight ? "text-primary" : "text-on-surface"}`}>
              {s.value}
            </div>
            <div className="text-[10px] font-mono text-on-surface/40">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tier breakdown */}
      <div className="mb-5">
        <p className="text-[10px] font-mono text-on-surface/30 mb-2">PRICABILITY (UNVALUED ITEMS)</p>
        <div className="space-y-1.5">
          {tierLabels.map((t) => {
            const count = data.by_tier[t.key] || 0;
            const pct = (count / tierMax) * 100;
            return (
              <div key={t.key} className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-on-surface/40 w-32 shrink-0">{t.label}</span>
                <div className="flex-1 h-3 rounded bg-white/[0.04] overflow-hidden">
                  <div className={`h-full rounded ${t.color}`} style={{ width: `${pct}%` }} />
                </div>
                <span className="text-[10px] font-mono text-on-surface/50 w-10 text-right">{count.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Data completeness */}
      <p className="text-[10px] font-mono text-on-surface/30 mb-4">
        AVG DATA COMPLETENESS: <span className="text-on-surface/60">{data.completeness_avg}%</span>
      </p>

      {/* Batch progress */}
      {batch?.status === "running" && (
        <div className="mb-4 p-3 rounded-lg bg-primary/5 border border-primary/20">
          <div className="flex justify-between text-xs font-mono mb-1">
            <span className="text-primary">Pricing {batch.completed} of {batch.total}...</span>
            <span className="text-on-surface/40">{batch.current_item?.slice(0, 40)}</span>
          </div>
          <div className="h-2 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${((batch.completed || 0) / (batch.total || 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {batch?.status === "completed" && batch.summary && (
        <div className="mb-4 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs font-mono">
          Batch complete: {batch.summary.priced} priced, {batch.summary.failed} failed
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-on-surface/70 hover:bg-white/[0.08] transition-colors disabled:opacity-40"
        >
          <MaterialIcon icon="download" className="text-[16px]" />
          {downloading ? "Generating..." : "Download Report"}
        </button>
        <button
          onClick={handleBatchPrice}
          disabled={batch?.status === "running"}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary/10 border border-primary/30 text-xs font-mono text-primary hover:bg-primary/20 transition-colors disabled:opacity-40"
        >
          <MaterialIcon icon="auto_fix_high" className="text-[16px]" />
          {batch?.status === "running" ? "Running..." : "Price Tier 1 & 2"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 23: Commit**

```bash
git add frontend/nova-app/components/dashboard/pricing-coverage.tsx
git commit -m "feat: add PricingCoverage dashboard widget"
```

### Task 9: Wire widget into dashboard page

**Files:**
- Modify: `frontend/nova-app/app/(app)/page.tsx`

- [ ] **Step 24: Replace Opportunities import and usage**

In `app/(app)/page.tsx`:
- Change import (line 6) from:
  ```tsx
  import { Opportunities } from "@/components/dashboard/opportunities";
  ```
  to:
  ```tsx
  import { PricingCoverage } from "@/components/dashboard/pricing-coverage";
  ```
- Change rendering (line 50) from:
  ```tsx
  <Opportunities />
  ```
  to:
  ```tsx
  <PricingCoverage />
  ```

- [ ] **Step 25: Verify build**

Run: `cd frontend/nova-app && npm run build 2>&1 | tail -5`
Expected: Build succeeds, no TypeScript errors

- [ ] **Step 26: Commit**

```bash
git add frontend/nova-app/app/\(app\)/page.tsx
git commit -m "feat: replace Market Opportunities with Pricing Coverage widget"
```

---

## Chunk 5: Visual Verification + Final Tests

### Task 10: Visual verification in browser

- [ ] **Step 27: Start dev servers and verify**

```bash
cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8100 --reload &
cd frontend/nova-app && npm run dev &
```

Navigate to `http://localhost:3000` and verify:
1. Dashboard loads without errors
2. Pricing Coverage widget appears with gradient progress bar
3. Stats row shows Total / Listed Price / Unvalued / AI Priced
4. Tier breakdown bars render correctly
5. "Download Report" button downloads an XLSX file
6. "Price Tier 1 & 2" button triggers batch pricing with progress indicator

- [ ] **Step 28: Run full test suite**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/ -v --timeout=30`
Expected: All tests PASS (existing + new)

- [ ] **Step 29: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address visual/test issues from verification"
```

---

## Test Plan Summary

| Test | Type | What it verifies |
|------|------|-----------------|
| `test_requires_auth` (x3) | Unit | All endpoints reject unauthenticated requests |
| `test_returns_coverage_stats` | Unit | Coverage endpoint returns all expected fields |
| `test_percentages_are_valid` | Unit | Percentages are 0-100, valued >= asking |
| `test_analyst_can_access` | Unit | Non-admin roles can view coverage stats |
| `test_returns_xlsx` | Unit | Report returns XLSX content type |
| `test_xlsx_has_expected_headers` | Unit | Report has all required column headers |
| `test_returns_job_id` | Unit | Batch pricing returns a job_id |
| `test_rejects_duplicate` | Unit | 409 when batch already running |
| Visual: gradient bar | Manual | Bar fills to correct %, gradient renders |
| Visual: download report | Manual | XLSX downloads with data, columns match spec |
| Visual: batch pricing | Manual | Progress indicator updates, stats refresh on complete |
| Existing test suite | Regression | No existing tests broken |
