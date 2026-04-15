# Fuelled Pricing Coverage — Design Spec

**Date**: 2026-04-15
**Branch**: `feature/fuelled-pricing-coverage`
**Goal**: Give Mark visibility into Fuelled inventory pricing gaps, surface data quality issues, and enable batch AI valuation of unpriced items.

## Context

A significant portion of Fuelled.com listings have no asking price — they're invisible to buyers filtering by price and impossible to comp against. Mark wants to drive toward 100% pricing coverage.

The exact counts are dynamic. The canonical queries that define the KPIs are specified in the Backend section below.

**Data quality observations** (unpriced items, as of 2026-04-15):
- Condition data is near 100%
- Make coverage ~80%, model coverage ~7%, year ~39%
- Zero hours data across all unpriced items

**Pricability tiers** (defined by available data):

| Tier | Criteria | Pricing confidence |
|------|----------|-------------------|
| 1 | Make + Model + Year | High |
| 2 | Make + Year | Medium |
| 3 | Make only | Low |
| 4 | Category only | Very low |

## Approach

**Phase A (this spec)**: Dashboard widget with two distinct metrics + downloadable report + batch valuation trigger. Internal only — AI valuations stored as `fair_value`, not published to fuelled.com.

**Phase C (future)**: Review-then-publish queue where someone approves AI valuations before they become asking prices.

## Two Distinct Metrics

The widget tracks two separate coverage numbers:

1. **Asking Price Coverage** — % of Fuelled listings with `asking_price > 0`. This is the public/buyer-facing number. It only changes when prices are set on fuelled.com.
2. **Internal Valuation Coverage** — % of Fuelled listings with `asking_price > 0 OR fair_value > 0`. This reflects what Nova knows internally. It increases as the AI prices items.

The gradient progress bar shows **Internal Valuation Coverage** (the number we can move). Asking Price Coverage is shown as a secondary stat so the gap between "what we know" and "what buyers see" is visible.

## Backend

### DB Columns (existing)

The `listings` table already has these columns — no migration needed:

- `fair_value DOUBLE PRECISION` — AI-generated FMV midpoint
- `last_valued_at TIMESTAMPTZ` — when it was last valued

Confidence is stored in a separate `fuelled_valuations` log table (see below), not on the listing itself.

### New table: `fuelled_valuations`

Created on first use (idempotent `CREATE TABLE IF NOT EXISTS`):

```sql
CREATE TABLE IF NOT EXISTS fuelled_valuations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL,
    fmv_low DOUBLE PRECISION,
    fmv_mid DOUBLE PRECISION,
    fmv_high DOUBLE PRECISION,
    confidence VARCHAR(10),
    tier INTEGER,
    data_completeness INTEGER,
    tools_used TEXT[],
    trace_id VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

This provides an audit trail — every valuation attempt is recorded, including failures. The listing's `fair_value` and `last_valued_at` are updated only on success.

### Canonical KPI queries

All coverage stats derive from these predicates:

```sql
-- Base population
WHERE source = 'fuelled' AND is_active = true

-- Asking price coverage
COUNT(CASE WHEN asking_price IS NOT NULL AND asking_price > 0 THEN 1 END)

-- Internal valuation coverage  
COUNT(CASE WHEN (asking_price > 0) OR (fair_value > 0) THEN 1 END)

-- AI-priced only
COUNT(CASE WHEN fair_value > 0 AND (asking_price IS NULL OR asking_price = 0) THEN 1 END)

-- Tier assignment
CASE
  WHEN make IS NOT NULL AND make != '' AND model IS NOT NULL AND model != '' AND year IS NOT NULL THEN 1
  WHEN make IS NOT NULL AND make != '' AND year IS NOT NULL THEN 2
  WHEN make IS NOT NULL AND make != '' THEN 3
  ELSE 4
END

-- Data completeness (0-100)
(CASE WHEN make IS NOT NULL AND make != '' THEN 25 ELSE 0 END)
+ (CASE WHEN model IS NOT NULL AND model != '' THEN 20 ELSE 0 END)
+ (CASE WHEN year IS NOT NULL THEN 25 ELSE 0 END)
+ (CASE WHEN hours IS NOT NULL THEN 15 ELSE 0 END)
+ (CASE WHEN horsepower IS NOT NULL THEN 10 ELSE 0 END)
+ (CASE WHEN condition IS NOT NULL AND condition != '' THEN 5 ELSE 0 END)
```

### New route file: `backend/app/api/fuelled_coverage.py`

Three endpoints, all admin-only (JWT auth required):

#### `GET /api/admin/fuelled/coverage`

Returns pricing coverage stats for the dashboard widget. All numbers are computed live from the canonical queries above.

```json
{
  "total": 0,
  "asking_price_count": 0,
  "asking_price_pct": 0.0,
  "valued_count": 0,
  "valued_pct": 0.0,
  "ai_only_count": 0,
  "unpriced": 0,
  "by_tier": {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0},
  "by_category": [{"category": "Tank", "unpriced": 0, "completeness_avg": 0}],
  "completeness_avg": 0
}
```

#### `POST /api/admin/fuelled/generate-report`

Generates an XLSX report of all unpriced Fuelled listings with data quality analysis.

**Columns**: Title, Category, Make, Model, Year, Condition, Hours, HP, Data Completeness %, Missing Fields, Days Listed, Pricability Tier, URL

Returns the file as a download (`Content-Disposition: attachment`). Uses `openpyxl` (already a dependency).

#### `POST /api/admin/fuelled/price-batch`

Triggers batch AI valuation of unpriced Fuelled items.

**Request body** (optional):
```json
{
  "tiers": [1, 2],
  "limit": 50
}
```

Defaults to tiers 1+2, limit 50 per run.

**Batch pricing mode**: The pricing query is constructed as a directive, not a question. Instead of "What is a 2018 Ariel JGK4 compressor worth?", it sends:

```
Provide a fair market value estimate for this equipment. Do not ask follow-up questions — use your best judgment with the data available. If critical data is missing, state your assumptions and provide a wider confidence range.

Equipment: {title}
Category: {category}
Manufacturer: {make}
Model: {model}
Year: {year}
Condition: {condition}
```

This prevents the agent from entering its follow-up-question branch (which fires when hours/specs are missing). The agent will estimate with assumptions and flag them in the response.

**Flow**:
1. Query unpriced Fuelled listings matching tier filter, ordered by tier ASC (best data first)
2. Create batch job in `_batch_jobs` dict (reuse existing pattern from `batch.py`)
3. For each item, build the directive query above
4. Call `run_pricing()` with 60s timeout
5. Check response: if `structured.valuation.fmv_mid` exists and is > 0, it's a success
6. On success: `UPDATE listings SET fair_value = fmv_mid, last_valued_at = NOW() WHERE id = :id`
7. Always: insert row into `fuelled_valuations` table (success or failure)
8. On failure (no fmv_mid, timeout, or error): log to valuations table with NULL values, skip listing
9. Return `job_id` for polling via existing `GET /api/price/batch/{job_id}/status`

**Idempotency**: Before starting, check if a job is already running for this endpoint (flag in `_batch_jobs`). Reject duplicate triggers with 409 Conflict. Items that already have `fair_value > 0` are skipped.

### Route registration

Add to `main.py`:
```python
from app.api.fuelled_coverage import router as fuelled_coverage_router
app.include_router(fuelled_coverage_router, prefix="/api/admin/fuelled")
```

## Frontend

### Replace Market Opportunities with Pricing Coverage Widget

**File**: `frontend/nova-app/components/dashboard/pricing-coverage.tsx`

Replaces `<Opportunities />` on the dashboard page.

**Layout**:

```
┌─────────────────────────────────────────────────────────┐
│  Fuelled Pricing Coverage                               │
│                                                         │
│  Internal Valuation Coverage              29.7%         │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  100%  │
│  ← gradient: primary(red/orange) → emerald green →      │
│                                                         │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │ 6,975│  │ 2,070│  │ 4,905│  │    0 │               │
│  │Total │  │Listed│  │Unvalu│  │  AI  │               │
│  │      │  │Price │  │  ed  │  │Priced│               │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
│                                                         │
│  Asking Price (public): 29.7%                           │
│                                                         │
│  Pricability    Tier 1 ██ High                          │
│                 Tier 2 ████████████ Medium               │
│                 Tier 3 ████████████████ Low              │
│                 Tier 4 ████████ Very Low                 │
│                                                         │
│  Avg Data Completeness: 42%                             │
│                                                         │
│  [ Download Report ]          [ Price Tier 1 & 2 ]      │
└─────────────────────────────────────────────────────────┘
```

**Gradient bar**: CSS `background: linear-gradient(to right, var(--color-primary), #f59e0b, #10b981)` on the filled portion. Unfilled portion is `bg-white/[0.04]`. Rounded corners. The fill width is `valued_pct%`.

**Two coverage numbers**: The gradient bar and headline show Internal Valuation Coverage (what we can move). Below the stats row, "Asking Price (public): X%" shows the buyer-facing number as secondary context.

**Buttons**:
- "Download Report" — calls `POST /api/admin/fuelled/generate-report`, triggers file download
- "Price Tier 1 & 2" — calls `POST /api/admin/fuelled/price-batch`, shows inline progress bar with polling

**During batch pricing**: The button changes to a progress indicator ("Pricing 12 of 50...") using the same polling pattern as batch-upload.tsx.

### Dashboard page change

In `app/(app)/page.tsx`, replace `<Opportunities />` with `<PricingCoverage />`.

### API wrapper

Add to `lib/api.ts`:
```typescript
export async function fetchFuelledCoverage() { ... }
export async function downloadFuelledReport() { ... }
export async function startFuelledPriceBatch(tiers?: number[], limit?: number) { ... }
```

## Files to create/modify

| Action | File |
|--------|------|
| Create | `backend/app/api/fuelled_coverage.py` (~180 lines) |
| Modify | `backend/app/main.py` (add router) |
| Create | `frontend/nova-app/components/dashboard/pricing-coverage.tsx` (~200 lines) |
| Modify | `frontend/nova-app/app/(app)/page.tsx` (swap Opportunities → PricingCoverage) |
| Modify | `frontend/nova-app/lib/api.ts` (add 3 functions) |

## What this does NOT include

- Publishing AI prices to fuelled.com (phase C)
- Review/approval queue (phase C)
- Dedicated /pricing-coverage page with filterable table (phase B)
- Automatic nightly pricing cron (phase C)
- Embeddings or vector search for comps (separate initiative)
