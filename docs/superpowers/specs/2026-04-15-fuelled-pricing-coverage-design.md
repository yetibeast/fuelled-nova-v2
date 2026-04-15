# Fuelled Pricing Coverage — Design Spec

**Date**: 2026-04-15
**Branch**: `feature/fuelled-pricing-coverage`
**Goal**: Give Mark visibility into what % of Fuelled inventory has prices, surface data gaps, and enable batch AI pricing of unpriced items.

## Context

Fuelled.com has 6,975 listings. Only 2,070 (29.7%) have an asking price. The remaining 4,905 items sit unpriced — invisible to buyers filtering by price and impossible to comp against. Mark wants 100% pricing coverage.

**Data quality of unpriced items:**

| Tier | Criteria | Count | Pricing confidence |
|------|----------|------:|-------------------|
| 1 | Make + Model + Year | 212 | High |
| 2 | Make + Year | 1,565 | Medium |
| 3 | Make only | 2,131 | Low |
| 4 | Category only | 997 | Very low |

All items have condition data (100%). Zero have hours. Model coverage is 7%.

## Approach

**Phase A (this spec)**: Dashboard widget + downloadable report + batch pricing trigger. Internal only — AI prices stored as `fair_value`, not published to fuelled.com.

**Phase C (future)**: Review-then-publish queue where someone approves AI prices before they go live.

## Backend

### DB Migration

Add columns to `listings` table (idempotent, runs on startup):

```sql
ALTER TABLE listings ADD COLUMN IF NOT EXISTS fair_value DOUBLE PRECISION;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS fair_value_confidence VARCHAR(10);
ALTER TABLE listings ADD COLUMN IF NOT EXISTS fair_value_at TIMESTAMPTZ;
```

`fair_value` stores the AI-generated FMV midpoint. `fair_value_confidence` stores HIGH/MEDIUM/LOW. `fair_value_at` records when it was priced.

### New route file: `backend/app/api/fuelled_coverage.py`

Three endpoints, all admin-only (JWT auth required):

#### `GET /api/admin/fuelled/coverage`

Returns pricing coverage stats for the dashboard widget.

```json
{
  "total": 6975,
  "priced": 2070,
  "unpriced": 4905,
  "coverage_pct": 29.7,
  "ai_priced": 0,
  "by_tier": {
    "tier_1": 212,
    "tier_2": 1565,
    "tier_3": 2131,
    "tier_4": 997
  },
  "by_category": [
    {"category": "Tank", "total": 1009, "completeness_avg": 45},
    {"category": "Separator", "total": 574, "completeness_avg": 52}
  ],
  "completeness_avg": 42
}
```

**Tier logic** (SQL CASE):
- Tier 1: `make IS NOT NULL AND model IS NOT NULL AND year IS NOT NULL`
- Tier 2: `make IS NOT NULL AND year IS NOT NULL`
- Tier 3: `make IS NOT NULL`
- Tier 4: everything else

**Completeness score** per item (0-100):
- make present: +25
- model present: +20
- year present: +25
- hours present: +15
- horsepower present: +10
- condition present: +5

#### `POST /api/admin/fuelled/generate-report`

Generates an XLSX report of all unpriced Fuelled listings with data quality analysis.

**Columns**: Title, Category, Make, Model, Year, Condition, Hours, HP, Data Completeness %, Missing Fields, Days Listed, Pricability Tier, URL

Returns the file as a download (`Content-Disposition: attachment`).

Uses `openpyxl` (already a dependency for RCN loading).

#### `POST /api/admin/fuelled/price-batch`

Triggers batch AI pricing of unpriced Fuelled items.

**Request body** (optional):
```json
{
  "tiers": [1, 2],
  "limit": 50
}
```

Defaults to tiers 1+2, limit 50 per run.

**Flow**:
1. Query unpriced Fuelled listings matching tier filter
2. Create batch job in `_batch_jobs` dict (reuse existing pattern from `batch.py`)
3. For each item, build a pricing query from title + make + model + year + condition
4. Call `run_pricing()` with 60s timeout
5. On success: `UPDATE listings SET fair_value = fmv_mid, fair_value_confidence = confidence, fair_value_at = NOW() WHERE id = :id`
6. Return `job_id` for polling via existing `GET /api/price/batch/{job_id}/status`

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
│  Fuelled Pricing Coverage                    29.7%      │
│                                                         │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  100%  │
│  ← gradient: primary(red/orange) → emerald green →      │
│                                                         │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │ 6,975│  │ 2,070│  │ 4,905│  │    0 │               │
│  │Total │  │Priced│  │ Need │  │  AI  │               │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
│                                                         │
│  Pricability    Tier 1 ██ 212                           │
│                 Tier 2 ████████████ 1,565               │
│                 Tier 3 ████████████████ 2,131           │
│                 Tier 4 ████████ 997                     │
│                                                         │
│  Avg Data Completeness: 42%                             │
│                                                         │
│  [ Download Report ]          [ Price Tier 1 & 2 ]      │
└─────────────────────────────────────────────────────────┘
```

**Gradient bar**: CSS `background: linear-gradient(to right, var(--color-primary), #f59e0b, #10b981)` on the filled portion. Unfilled portion is `bg-white/[0.04]`. Rounded corners. The fill width is `coverage_pct%`.

**Tier bars**: Small horizontal bars, proportional width, using the existing glass-card style with subtle opacity.

**Buttons**:
- "Download Report" — calls `POST /api/admin/fuelled/generate-report`, triggers file download
- "Price Tier 1 & 2" — calls `POST /api/admin/fuelled/price-batch`, shows inline progress bar with polling

**During batch pricing**: The button changes to a progress indicator ("Pricing 12 of 50...") using the same polling pattern as batch-upload.tsx.

### Dashboard page change

In `app/(app)/page.tsx`, replace:
```tsx
<Opportunities />
```
with:
```tsx
<PricingCoverage />
```

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
| Create | `backend/app/api/fuelled_coverage.py` (~150 lines) |
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
