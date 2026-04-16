# Competitive Stale Inventory Acquisition — Design Spec

**Date**: 2026-04-15
**Branch**: `feature/competitive-stale-acquisition`
**Goal**: Identify stale competitor inventory that is likely buyable, rank it as acquisition targets, and let Fuelled ops promote candidates into an internal queue with draft listing packets.

## Context

The current competitive page already shows summary counts, below-market deals, and a stale-inventory metric. That is useful as market intelligence, but it is not yet an acquisition workflow.

Mark's operating idea is straightforward:

1. Detect competitor listings that have sat for an unusually long time.
2. Treat that stale inventory as a buy-side signal.
3. Review the best candidates internally.
4. Create a Fuelled-ready draft packet so the team can pursue the asset and market it on Fuelled if they win it.

Two gaps exist today:

- The current stale query is not actually competitor-only in all places.
- The app has no durable concept of an "acquisition target"; it only has raw scraped listings.

## Product Decision

This feature introduces a new internal workflow concept:

- **Competitor listing**: raw scraped row from `listings`
- **Stale candidate**: a competitor listing that meets age/recency/price rules
- **Acquisition target**: an internal record created from a stale candidate and tracked through review/outreach
- **Draft Fuelled listing packet**: a normalized snapshot generated from an acquisition target for internal listing creation later

The shared `listings` feed remains the read-only source of truth for market observations. Workflow state does not belong there.

## Approach

**Phase A (this spec)**: Fix stale detection, rank stale competitor listings as acquisition candidates, and let admins promote them into a managed acquisition queue with draft listing payloads.

**Phase B (future)**: Enrich promoted targets with pricing-v2 output so each candidate has FMV, recommended list price, and buy-side notes.

**Phase C (future)**: Push approved draft packets into a real Fuelled listing creation flow once a publish path exists.

## Core Rules

### 1. Competitor-only means competitor-only

All stale and acquisition queries must explicitly exclude Fuelled inventory:

```sql
LOWER(source) != 'fuelled'
```

This applies to both the summary metric and the stale candidate feed.

### 2. Staleness is category-relative

A single global threshold of 365 days is too blunt. Some equipment types move much faster than others.

Phase A uses a small code-defined threshold map:

| Category bucket | Threshold |
|-----------------|-----------|
| Compressors, engines, generators, VRUs, pump jacks | 180 days |
| Separators, treaters, dehydrators, line heaters, scrubbers | 270 days |
| Tanks, vessels, trailers, storage, miscellaneous heavy iron | 365 days |
| Unknown/default | 365 days |

Implementation can map from `category` or `category_normalized` by simple normalization plus keyword matching. Precision is less important than consistency in V1.

### 3. "Stale" and "promotable" are not the same thing

A listing can be stale without being a good acquisition candidate.

Phase A stale-candidate rules:

- `LOWER(source) != 'fuelled'`
- `asking_price > 0`
- `last_seen >= NOW() - INTERVAL '30 days'`
- `days_listed >= threshold_for_category`

Phase A promotable rules:

- meets stale-candidate rules
- not from an auction-only source
- enough market context exists to rank it

Auction-like sources should still be visible in the stale feed, but not auto-promotable. Initial excluded sources:

- `ritchiebros`
- `ironplanet`
- `govdeals`
- `bidspotter`
- `allsurplus`
- `energyauctions`

That list can stay code-defined in V1.

## Ranking Model

Each stale candidate gets an `acquisition_score` from 0-100.

The score is for prioritization, not automated buying.

### Score components

1. **Age pressure** (0-35)
   Higher when the listing has exceeded its category threshold by a larger margin.

2. **Negotiability** (0-20)
   Higher when the current asking price is above the peer median, because stale overpriced inventory is more likely to have room for negotiation.

3. **Liquidity** (0-20)
   Higher when the category has enough live priced peers to support resale confidence.

4. **Data quality** (0-15)
   Higher when make, model, year, condition, hours, and location are present.

5. **Source quality** (0-10)
   Higher for dealer/classified inventory than auction-style listings.

### Peer median

Phase A uses a simple peer-median estimate:

- same normalized category
- priced listings only
- competitor inventory only
- optionally narrow by year band when the candidate has a year and enough peers remain

If fewer than 5 peers exist, `peer_median` may be null and the ranking model should cap the market-based score instead of inventing precision.

## Persistence Boundary

The shared scrape database is not where acquisition workflow state should live.

### New state store

Use a separate app-owned Postgres database provisioned on Railway:

```env
STATE_DATABASE_URL=postgresql+asyncpg://...
```

This must be a different database from the shared scrape source in `DATABASE_URL`.

Rules:

- `DATABASE_URL` remains the read-only listings source
- `STATE_DATABASE_URL` is the only place this feature may write queue state
- do not fall back to `DATABASE_URL` if `STATE_DATABASE_URL` is missing

This keeps `listings` read-only while still allowing durable queue state across Railway deploys and restarts.

### New table: `competitive_acquisition_targets`

```sql
CREATE TABLE IF NOT EXISTS competitive_acquisition_targets (
    id TEXT PRIMARY KEY,
    source_listing_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    asking_price REAL,
    location TEXT,
    url TEXT,
    first_seen TEXT,
    last_seen TEXT,
    days_listed INTEGER,
    stale_threshold_days INTEGER,
    peer_median REAL,
    peer_count INTEGER,
    acquisition_score INTEGER NOT NULL,
    promotable INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'new',
    assigned_to TEXT,
    notes TEXT,
    draft_payload TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### New table: `competitive_acquisition_events`

```sql
CREATE TABLE IF NOT EXISTS competitive_acquisition_events (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_note TEXT,
    actor_id TEXT,
    created_at TEXT NOT NULL
);
```

This gives the queue a durable audit trail without mutating `listings`.

### Table initialization

Phase A can use idempotent startup SQL against the state database only:

- `CREATE TABLE IF NOT EXISTS competitive_acquisition_targets`
- `CREATE TABLE IF NOT EXISTS competitive_acquisition_events`
- indexes for `status`, `source_listing_id`, and `updated_at`

That is acceptable here because these tables live in the app-owned Railway Postgres database, not the shared scrape database.

## Backend

### Existing route to fix: `backend/app/api/competitive.py`

Fix the stale summary and stale list queries so they are explicitly competitor-only.

### New read endpoint: `GET /api/competitive/stale-targets`

Auth level: authenticated user

Purpose: return ranked stale candidates for the competitive page.

Optional query params:

- `promotable_only=true|false`
- `min_score=0-100`
- `limit=25` default

Response shape:

```json
[
  {
    "source_listing_id": "abc123",
    "title": "2018 Ariel JGK/4 Compressor Package",
    "source": "machinio",
    "category": "compressors",
    "asking_price": 425000,
    "location": "Alberta",
    "url": "https://...",
    "first_seen": "2025-02-01T00:00:00Z",
    "last_seen": "2026-04-12T00:00:00Z",
    "days_listed": 438,
    "stale_threshold_days": 180,
    "peer_median": 365000,
    "peer_count": 12,
    "acquisition_score": 82,
    "promotable": true,
    "reason": "Long-overdue compressor listing with strong peer coverage"
  }
]
```

### New admin route file: `backend/app/api/competitive_queue.py`

All endpoints in this file are admin-only.

#### `GET /api/admin/competitive/acquisition/summary`

Returns queue counts:

```json
{
  "total": 0,
  "new": 0,
  "watching": 0,
  "contacted": 0,
  "negotiating": 0,
  "drafted": 0,
  "won": 0,
  "lost": 0,
  "archived": 0
}
```

#### `GET /api/admin/competitive/acquisition/targets`

Returns promoted targets from the state DB.

Filters:

- `status`
- `assigned_to`
- `limit`

#### `POST /api/admin/competitive/acquisition/promote`

Creates or returns an acquisition target from a stale candidate.

Request:

```json
{
  "source_listing_id": "abc123",
  "note": "Looks like a dealer unit we should chase"
}
```

Behavior:

1. Re-read the candidate from `listings`
2. Recompute stale status and ranking
3. Reject non-promotable candidates with `409`
4. Snapshot source fields into the state DB
5. Write a `promoted` event
6. Return the created or existing target

#### `POST /api/admin/competitive/acquisition/{target_id}/status`

Updates target status and records an event.

Allowed statuses:

- `new`
- `watching`
- `contacted`
- `negotiating`
- `drafted`
- `won`
- `lost`
- `archived`

#### `POST /api/admin/competitive/acquisition/{target_id}/draft`

Generates or refreshes the draft Fuelled listing payload.

The payload is internal only and does not publish anything. It should include:

```json
{
  "title": "2018 Ariel JGK/4 Compressor Package",
  "category": "compressors",
  "make": "Ariel",
  "model": "JGK/4",
  "year": 2018,
  "condition": "Used",
  "location": "Alberta",
  "competitor_source": "machinio",
  "competitor_url": "https://...",
  "competitor_asking_price": 425000,
  "peer_median": 365000,
  "peer_count": 12,
  "listing_notes": "Auto-generated from stale competitor inventory. Pricing review still required."
}
```

The payload is stored as JSON text on the acquisition target and returned to the client for review/copy/export.

## Frontend

### Competitive page

Keep the page at `frontend/nova-app/app/(app)/competitive/page.tsx`.

Add two distinct sections:

1. **Stale Acquisition Candidates**
   Read-only ranked feed from `GET /api/competitive/stale-targets`

2. **Acquisition Queue**
   Admin-only operational queue from `GET /api/admin/competitive/acquisition/targets`

### Candidate table

New component:

- `frontend/nova-app/components/competitive/stale-targets.tsx`

Columns:

- Equipment
- Category
- Asking Price
- Days Listed
- Threshold
- Peer Median
- Score
- Source
- Action

Actions:

- `Open source`
- `Promote` for admins when `promotable = true`

### Queue table

New component:

- `frontend/nova-app/components/competitive/acquisition-queue.tsx`

Columns:

- Equipment
- Status
- Score
- Asking Price
- Peer Median
- Assigned To
- Updated
- Actions

Actions:

- change status
- generate draft packet
- open competitor URL

### API wrappers

Add wrappers in `frontend/nova-app/lib/api.ts`:

- `fetchCompetitiveStaleTargets()`
- `fetchAcquisitionSummary()`
- `fetchAcquisitionTargets()`
- `promoteAcquisitionTarget()`
- `updateAcquisitionStatus()`
- `generateAcquisitionDraft()`

No Next.js proxy work is needed because `/api/:path*` already rewrites to the backend.

## Success Criteria

1. Competitive stale metrics exclude Fuelled inventory.
2. The competitive page shows a ranked stale-candidate feed instead of only a count.
3. Admins can promote a stale candidate into a durable queue.
4. Promoted targets can move through statuses without touching the shared `listings` table.
5. Each promoted target can generate a draft Fuelled listing packet for internal ops use.

## Out of Scope

- Auto-buying equipment
- Auto-publishing to Fuelled
- CRM or email outreach automation
- AI valuation of acquisition targets
- Changing scraper cadence or scrape schema
- Mutating the shared `listings` source table
