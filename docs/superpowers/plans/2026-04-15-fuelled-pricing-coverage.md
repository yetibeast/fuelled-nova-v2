# Fuelled Pricing Coverage Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard widget showing Fuelled inventory pricing coverage with downloadable report and batch AI valuation trigger.

**Architecture:** New backend route file (`fuelled_coverage.py`) with 3 endpoints + audit table. New frontend component (`pricing-coverage.tsx`) replacing Market Opportunities on the dashboard. Reuses existing batch job infrastructure and `run_pricing()` service.

**Tech Stack:** FastAPI, SQLAlchemy async, openpyxl, React/TypeScript, Tailwind v4

**Spec:** `docs/superpowers/specs/2026-04-15-fuelled-pricing-coverage-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/app/api/fuelled_coverage.py` | 3 API endpoints: coverage stats, report download, batch pricing |
| Create | `backend/tests/test_fuelled_coverage.py` | Tests for all 3 endpoints |
| Modify | `backend/tests/conftest.py` | Seed fuelled listings, patch new module, add mock SQL handlers |
| Modify | `backend/app/main.py:8,32` | Register new router |
| Create | `frontend/nova-app/components/dashboard/pricing-coverage.tsx` | Dashboard widget component |
| Modify | `frontend/nova-app/app/(app)/page.tsx:6,50` | Swap Opportunities → PricingCoverage |
| Modify | `frontend/nova-app/lib/api.ts` | Add 4 API wrapper functions |

---

## Chunk 1: Test Infrastructure + Coverage Stats Endpoint

### Task 0: Seed mock fuelled listings in conftest.py

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add fuelled listing seeds to _InMemoryDB and mock SQL handlers**

In `conftest.py`, add seed data to `_InMemoryDB.__init__()` (after `self.listings = []`):

```python
        # Seed fuelled listings for coverage tests
        self._seed_fuelled_listings()

    def _seed_fuelled_listings(self):
        """Seed realistic fuelled listings for pricing coverage tests."""
        import uuid as _uuid
        base = datetime.now(timezone.utc) - timedelta(days=30)
        seeds = [
            # Tier 1: make + model + year (2 items, 1 priced)
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "2019 Ariel JGK4 Compressor", "category": "Compressor Package", "make": "Ariel", "model": "JGK4", "year": 2019, "condition": "Good", "hours": None, "horsepower": None, "asking_price": 450000, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/1", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "2018 Ariel JGK2 Compressor", "category": "Compressor Package", "make": "Ariel", "model": "JGK2", "year": 2018, "condition": "Good", "hours": None, "horsepower": None, "asking_price": None, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/2", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
            # Tier 2: make + year (2 items, both unpriced)
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "1000 BBL Tank", "category": "Tank", "make": "Universal Industries", "model": None, "year": 2001, "condition": "For Sale", "hours": None, "horsepower": None, "asking_price": None, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/3", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "Separator 3-phase", "category": "Separator", "make": "CEDA", "model": None, "year": 2005, "condition": "Good", "hours": None, "horsepower": None, "asking_price": None, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/4", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
            # Tier 3: make only (1 item, unpriced)
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "Pump Jack", "category": "Pump Jack", "make": "Lufkin", "model": None, "year": None, "condition": "Fair", "hours": None, "horsepower": None, "asking_price": None, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/5", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
            # Tier 4: category only (1 item, unpriced)
            {"id": str(_uuid.uuid4()), "source": "fuelled", "title": "Miscellaneous valve assembly", "category": "Valve", "make": None, "model": None, "year": None, "condition": "Used", "hours": None, "horsepower": None, "asking_price": None, "fair_value": None, "is_active": True, "url": "https://fuelled.com/eq/6", "first_seen": base, "last_seen": datetime.now(timezone.utc)},
        ]
        self.listings.extend(seeds)
```

In `MockSession.execute()`, add handlers before the final `return MockResult()` for the fuelled coverage SQL patterns:

```python
        # ── Fuelled coverage stats ──────────────────────────────────
        if "source = 'fuelled'" in sql and "COUNT(*)" in sql.upper() and "AVG(" in sql.upper():
            fuelled = [l for l in self._db.listings if l.get("source") == "fuelled" and l.get("is_active")]
            total = len(fuelled)
            asking_ct = sum(1 for l in fuelled if (l.get("asking_price") or 0) > 0)
            valued_ct = sum(1 for l in fuelled if (l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)
            ai_only = sum(1 for l in fuelled if (l.get("fair_value") or 0) > 0 and not (l.get("asking_price") or 0) > 0)
            def _comp(l):
                s = 0
                if l.get("make"): s += 25
                if l.get("model"): s += 20
                if l.get("year") is not None: s += 25
                if l.get("hours") is not None: s += 15
                if l.get("horsepower") is not None: s += 10
                if l.get("condition"): s += 5
                return s
            avg_comp = round(sum(_comp(l) for l in fuelled) / max(total, 1), 1)
            return MockResult([{0: total, 1: asking_ct, 2: valued_ct, 3: ai_only, 4: avg_comp}])

        # Fuelled tier breakdown
        if "source = 'fuelled'" in sql and "tier" in sql.lower() and "GROUP BY" in sql.upper():
            fuelled_unvalued = [l for l in self._db.listings
                                if l.get("source") == "fuelled" and l.get("is_active")
                                and not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            tiers = {1: 0, 2: 0, 3: 0, 4: 0}
            for l in fuelled_unvalued:
                if l.get("make") and l.get("model") and l.get("year") is not None: tiers[1] += 1
                elif l.get("make") and l.get("year") is not None: tiers[2] += 1
                elif l.get("make"): tiers[3] += 1
                else: tiers[4] += 1
            rows = [{"tier": k, 0: k, "cnt": v, 1: v} for k, v in tiers.items() if v > 0]
            return MockResult(rows)

        # Fuelled category breakdown
        if "source = 'fuelled'" in sql and "category" in sql.lower() and "GROUP BY" in sql.upper() and "LIMIT" in sql.upper():
            from collections import Counter
            fuelled_unvalued = [l for l in self._db.listings
                                if l.get("source") == "fuelled" and l.get("is_active")
                                and not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            cats = Counter(l.get("category", "Unknown") for l in fuelled_unvalued)
            rows = [{0: cat, 1: cnt, 2: 30.0} for cat, cnt in cats.most_common(15)]
            return MockResult(rows)

        # Fuelled report query (SELECT with ORDER BY first_seen)
        if "source = 'fuelled'" in sql and "first_seen" in sql.lower() and "ORDER BY" in sql.upper():
            fuelled_unvalued = [l for l in self._db.listings
                                if l.get("source") == "fuelled" and l.get("is_active")
                                and not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            rows = [{
                "title": l.get("title"), "category": l.get("category"), "make": l.get("make"),
                "model": l.get("model"), "year": l.get("year"), "condition": l.get("condition"),
                "hours": l.get("hours"), "horsepower": l.get("horsepower"), "url": l.get("url"),
                "first_seen": l.get("first_seen"),
            } for l in fuelled_unvalued]
            return MockResult(rows)

        # Fuelled batch query (SELECT id, title, ... LIMIT)
        if "source = 'fuelled'" in sql and "LIMIT" in sql.upper() and "id" in sql and "title" in sql:
            fuelled_unvalued = [l for l in self._db.listings
                                if l.get("source") == "fuelled" and l.get("is_active")
                                and not ((l.get("asking_price") or 0) > 0 or (l.get("fair_value") or 0) > 0)]
            lim = params.get("lim", 50) if params else 50
            rows = [{
                "id": l["id"], "title": l.get("title"), "category": l.get("category"),
                "make": l.get("make"), "model": l.get("model"), "year": l.get("year"),
                "condition": l.get("condition"), "hours": l.get("hours"), "horsepower": l.get("horsepower"),
            } for l in fuelled_unvalued[:lim]]
            return MockResult(rows)

        # INSERT INTO fuelled_valuations — no-op
        if "fuelled_valuations" in sql and "INSERT" in sql.upper():
            return MockResult(rowcount=1)

        # UPDATE listings SET fair_value — apply to in-memory
        if "UPDATE listings SET fair_value" in sql:
            lid = params.get("id") if params else None
            fv = params.get("fv") if params else None
            if lid and fv:
                for l in self._db.listings:
                    if l["id"] == lid:
                        l["fair_value"] = fv
                        break
            return MockResult(rowcount=1)
```

Update `_patch_db` fixture to patch the new module:

```python
@pytest.fixture(autouse=True)
def _patch_db():
    global _db
    _db = _InMemoryDB()

    from app.api import conversations, evidence, admin_scrapers, fuelled_coverage
    conversations._tables_ready = False
    evidence._tables_ready = False
    admin_scrapers._tables_ready = False
    fuelled_coverage._table_init = False

    with patch("app.db.session.get_session", _mock_get_session), \
         patch("app.api.conversations.get_session", _mock_get_session), \
         patch("app.api.evidence.get_session", _mock_get_session), \
         patch("app.api.admin_scrapers.get_session", _mock_get_session), \
         patch("app.api.fuelled_coverage.get_session", _mock_get_session):
        yield
```

- [ ] **Step 2: Commit conftest changes**

```bash
git add backend/tests/conftest.py
git commit -m "test: seed fuelled listings + mock SQL for coverage tests"
```

### Task 1: Write and pass coverage endpoint tests

**Files:**
- Create: `backend/tests/test_fuelled_coverage.py`
- Create: `backend/app/api/fuelled_coverage.py`
- Modify: `backend/app/main.py`

- [ ] **Step 3: Write tests for GET /admin/fuelled/coverage**

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
        # All expected keys present
        for key in ["total", "asking_price_count", "asking_price_pct", "valued_count",
                     "valued_pct", "ai_only_count", "unpriced", "by_tier", "by_category", "completeness_avg"]:
            assert key in data, f"Missing key: {key}"
        # Tier keys
        for k in ["tier_1", "tier_2", "tier_3", "tier_4"]:
            assert k in data["by_tier"]

    def test_percentages_are_valid(self, client, admin_headers):
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        data = resp.json()
        assert 0 <= data["asking_price_pct"] <= 100
        assert 0 <= data["valued_pct"] <= 100
        assert data["valued_pct"] >= data["asking_price_pct"]

    def test_counts_match_seeds(self, client, admin_headers):
        """Verify against conftest seed data: 6 fuelled listings, 1 priced."""
        resp = client.get("/api/admin/fuelled/coverage", headers=admin_headers)
        data = resp.json()
        assert data["total"] == 6
        assert data["asking_price_count"] == 1
        assert data["unpriced"] == 5

    def test_analyst_can_view(self, client, user_headers):
        """Coverage stats are read-only — all roles can access."""
        resp = client.get("/api/admin/fuelled/coverage", headers=user_headers)
        assert resp.status_code == 200
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: FAIL — 404 route not found

- [ ] **Step 5: Implement coverage endpoint + register router**

Create `backend/app/api/fuelled_coverage.py` with the coverage endpoint (see spec for canonical SQL).

In `backend/app/main.py`:
- Add `fuelled_coverage` to the import line (line 8)
- Add `app.include_router(fuelled_coverage.router, prefix="/api")` after existing routers

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/app/main.py backend/tests/test_fuelled_coverage.py
git commit -m "feat: add GET /admin/fuelled/coverage endpoint with tests"
```

---

## Chunk 2: Report Download Endpoint

### Task 2: Write and pass report endpoint tests

**Files:**
- Modify: `backend/tests/test_fuelled_coverage.py`
- Modify: `backend/app/api/fuelled_coverage.py`

- [ ] **Step 8: Add report tests**

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
        for col in ["Title", "Data Completeness %", "Missing Fields", "Pricability Tier", "Days Listed", "URL"]:
            assert col in headers, f"Missing column: {col}"

    def test_report_row_count_matches_unpriced(self, client, admin_headers):
        import io
        from openpyxl import load_workbook
        resp = client.post("/api/admin/fuelled/generate-report", headers=admin_headers)
        wb = load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        # 5 unpriced items from seeds + 1 header row
        assert ws.max_row == 6
```

- [ ] **Step 9: Run tests to verify report tests fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py::TestFuelledReport -v`
Expected: FAIL

- [ ] **Step 10: Implement report endpoint**

Add the XLSX generation endpoint to `fuelled_coverage.py`. Uses `openpyxl.Workbook`, computes data completeness and missing fields per row, returns as `StreamingResponse` with attachment header.

- [ ] **Step 11: Run all tests**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All 9 tests PASS

- [ ] **Step 12: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/tests/test_fuelled_coverage.py
git commit -m "feat: add POST /admin/fuelled/generate-report XLSX download"
```

---

## Chunk 3: Batch Pricing Endpoint

### Task 3: Write and pass batch pricing tests

**Files:**
- Modify: `backend/tests/test_fuelled_coverage.py`
- Modify: `backend/app/api/fuelled_coverage.py`

- [ ] **Step 13: Add batch pricing tests**

Append to `test_fuelled_coverage.py`:

```python
class TestFuelledPriceBatch:
    """POST /api/admin/fuelled/price-batch"""

    def test_requires_auth(self, client):
        resp = client.post("/api/admin/fuelled/price-batch")
        assert resp.status_code == 401

    def test_analyst_cannot_trigger(self, client, user_headers):
        """Batch pricing is admin-only — analysts get 403."""
        resp = client.post(
            "/api/admin/fuelled/price-batch",
            headers=user_headers,
            json={"tiers": [1], "limit": 2},
        )
        assert resp.status_code == 403

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


class TestFuelledPriceStatus:
    """GET /api/admin/fuelled/price-batch/status"""

    def test_returns_idle_when_no_job(self, client, admin_headers):
        resp = client.get("/api/admin/fuelled/price-batch/status", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "idle"
```

- [ ] **Step 14: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py::TestFuelledPriceBatch -v`
Expected: FAIL

- [ ] **Step 15: Implement batch pricing endpoint + audit table**

Add to `fuelled_coverage.py`:

**Key design decisions:**
- Import `_require_admin` from `app.api.calibration` (checks `role == "admin"`, returns 403 for non-admins)
- Audit table uses app-generated UUIDs (`str(uuid.uuid4())`), not `gen_random_uuid()`
- Audit table includes `status VARCHAR(10)` and `error_reason TEXT` columns for failure tracking
- Directive prompt tells agent not to ask follow-up questions
- Validates `fmv_mid > 0` before writing to listings
- Idempotency: rejects with 409 if a job is already running

```python
# fuelled_valuations table DDL — note: NO gen_random_uuid(), app generates UUIDs
_VALUATIONS_DDL = """
CREATE TABLE IF NOT EXISTS fuelled_valuations (
    id UUID PRIMARY KEY,
    listing_id UUID NOT NULL,
    fmv_low DOUBLE PRECISION,
    fmv_mid DOUBLE PRECISION,
    fmv_high DOUBLE PRECISION,
    confidence VARCHAR(10),
    status VARCHAR(10) NOT NULL DEFAULT 'success',
    error_reason TEXT,
    tier INTEGER,
    data_completeness INTEGER,
    tools_used TEXT,
    trace_id VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""
```

Batch pricing uses `_require_admin` (not `_require_auth`):
```python
from app.api.calibration import _require_admin

@router.post("/admin/fuelled/price-batch")
async def fuelled_price_batch(body: dict | None = None, authorization: str = Header(None)):
    _require_admin(authorization)  # 403 for non-admin
    ...
```

- [ ] **Step 16: Run all tests**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/test_fuelled_coverage.py -v`
Expected: All 14 tests PASS

- [ ] **Step 17: Commit**

```bash
git add backend/app/api/fuelled_coverage.py backend/tests/test_fuelled_coverage.py
git commit -m "feat: add POST /admin/fuelled/price-batch + audit table"
```

---

## Chunk 4: Frontend — API Wrappers + Dashboard Widget

### Task 4: Add API wrapper functions

**Files:**
- Modify: `frontend/nova-app/lib/api.ts`

- [ ] **Step 18: Add 4 API functions**

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

- [ ] **Step 19: Commit**

```bash
git add frontend/nova-app/lib/api.ts
git commit -m "feat: add fuelled coverage API wrappers"
```

### Task 5: Create pricing coverage dashboard widget

**Files:**
- Create: `frontend/nova-app/components/dashboard/pricing-coverage.tsx`

- [ ] **Step 20: Create the component**

Component includes:
- Gradient progress bar (linear-gradient from `#EF5D28` → `#f59e0b` → `#10b981`)
- Stats row: Total / Listed Price / Unvalued / AI Priced
- Secondary text: "Asking price (public): X%"
- Tier breakdown with horizontal bars
- Data completeness average
- Batch pricing progress indicator (polls every 2s when running)
- Two action buttons: Download Report + Price Tier 1 & 2
- Loading skeleton with `animate-pulse`

See spec wireframe for exact layout. Follow patterns from `opportunities.tsx` — `"use client"`, `useState/useEffect`, glass-card styling.

- [ ] **Step 21: Commit**

```bash
git add frontend/nova-app/components/dashboard/pricing-coverage.tsx
git commit -m "feat: add PricingCoverage dashboard widget"
```

### Task 6: Wire widget into dashboard page

**Files:**
- Modify: `frontend/nova-app/app/(app)/page.tsx`

- [ ] **Step 22: Replace Opportunities with PricingCoverage**

Change import (line 6):
```tsx
// OLD: import { Opportunities } from "@/components/dashboard/opportunities";
import { PricingCoverage } from "@/components/dashboard/pricing-coverage";
```

Change rendering (line 50):
```tsx
// OLD: <Opportunities />
<PricingCoverage />
```

- [ ] **Step 23: Verify build**

Run: `cd frontend/nova-app && npm run build 2>&1 | tail -5`
Expected: Build succeeds, no TypeScript errors

- [ ] **Step 24: Commit**

```bash
git add frontend/nova-app/app/\(app\)/page.tsx
git commit -m "feat: replace Market Opportunities with Pricing Coverage widget"
```

---

## Chunk 5: Visual Verification + Regression Tests

### Task 7: Visual and regression verification

- [ ] **Step 25: Start dev servers and verify visually**

```bash
cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8100 --reload &
cd frontend/nova-app && npm run dev &
```

Navigate to `http://localhost:3000` and verify:
1. Dashboard loads — Pricing Coverage widget visible
2. Gradient progress bar renders correctly
3. Stats row shows correct numbers
4. Tier breakdown bars are proportional
5. "Download Report" downloads an XLSX
6. XLSX has correct columns and data
7. "Price Tier 1 & 2" triggers batch with progress indicator

- [ ] **Step 26: Run full backend test suite**

Run: `cd backend && PYTHONPATH=. python3 -m pytest tests/ -v --timeout=30`
Expected: All tests PASS — no regressions

- [ ] **Step 27: Fix any issues and commit**

```bash
git add -A && git commit -m "fix: address issues from visual/regression verification"
```

---

## Test Plan Summary

| Test | Type | Verifies |
|------|------|----------|
| `TestFuelledCoverage::test_requires_auth` | Unit | 401 without token |
| `TestFuelledCoverage::test_returns_coverage_stats` | Unit | All response fields present |
| `TestFuelledCoverage::test_percentages_are_valid` | Unit | 0-100, valued >= asking |
| `TestFuelledCoverage::test_counts_match_seeds` | Unit | Numbers match conftest seeds |
| `TestFuelledCoverage::test_analyst_can_view` | Unit | Read-only for all roles |
| `TestFuelledReport::test_requires_auth` | Unit | 401 without token |
| `TestFuelledReport::test_returns_xlsx` | Unit | XLSX content type |
| `TestFuelledReport::test_xlsx_has_expected_headers` | Unit | All required columns |
| `TestFuelledReport::test_report_row_count` | Unit | Matches unpriced count |
| `TestFuelledPriceBatch::test_requires_auth` | Unit | 401 without token |
| `TestFuelledPriceBatch::test_analyst_cannot_trigger` | Unit | **403 for non-admin** |
| `TestFuelledPriceBatch::test_returns_job_id` | Unit | Job created |
| `TestFuelledPriceBatch::test_rejects_duplicate` | Unit | 409 idempotency |
| `TestFuelledPriceStatus::test_idle` | Unit | Idle when no job |
| Visual: gradient bar | Manual | Renders, fills correctly |
| Visual: download report | Manual | XLSX downloads with data |
| Visual: batch pricing | Manual | Progress updates, stats refresh |
| Regression suite | Automated | No existing tests broken |
