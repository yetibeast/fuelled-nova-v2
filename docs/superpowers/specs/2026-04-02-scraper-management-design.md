# Scraper Management & Sold Price Harvester — Design Spec
**Date:** April 2, 2026
**Status:** Approved
**Branch:** TBD (from main)

---

## Problem

1. **No scraper management.** V2 scrapers page is read-only — shows listing counts from the DB but can't add, remove, pause, schedule, or trigger scrapers.
2. **No run history.** `scrape_targets` and `scrape_runs` tables don't exist in V2. No visibility into when scrapers last ran, what they found, or what failed.
3. **No sold prices.** Auction sites (BidSpotter 10K+, GovDeals 1K, Ritchie Bros 180) have `auction_end` dates but zero `final_price` values. The best comp data — actual transaction prices — isn't being captured.
4. **Manual execution only.** Scrapers are run by hand from CLI. No scheduling, no on-demand trigger from the app.

---

## Architecture

```
┌──────────────────────┐     Tailscale      ┌──────────────────────┐
│   Railway (Cloud)    │◄──────────────────►│   Proxmox (Local)    │
│                      │                    │                      │
│  Nova Backend (API)  │   POST /run/{name} │  Scraper Runner      │
│  Nova Frontend (UI)  │   POST /harvest    │  - scrapekit (11)    │
│  PostgreSQL (DB)     │                    │  - standalone (3)    │
│                      │                    │  - sold harvester    │
│  scrape_targets      │◄── reads/writes ──►│  cron (every 15min)  │
│  scrape_runs         │                    │                      │
│  listings            │                    │                      │
└──────────────────────┘                    └──────────────────────┘
```

- **Nova** manages configuration (CRUD) and displays status
- **Proxmox** executes scrapers and writes results
- **Tailscale** connects them securely (Railway Tailscale sidecar → Proxmox tailnet)
- **PostgreSQL** on Railway is the shared state — both sides read/write

---

## Database Schema

### scrape_targets

```sql
CREATE TABLE IF NOT EXISTS scrape_targets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT UNIQUE NOT NULL,
    url               TEXT,
    status            TEXT NOT NULL DEFAULT 'active',      -- active, paused, disabled
    scraper_type      TEXT NOT NULL DEFAULT 'scrapekit',   -- scrapekit, standalone, harvester
    schedule_cron     TEXT,                                 -- e.g., '0 */6 * * *', null = manual
    last_run_at       TIMESTAMPTZ,
    next_run_at       TIMESTAMPTZ,
    run_requested_at  TIMESTAMPTZ,                         -- set by "Run Now", cleared after run
    health_pct        INTEGER DEFAULT 100,
    total_items       INTEGER DEFAULT 0,
    items_with_price  INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

### scrape_runs

```sql
CREATE TABLE IF NOT EXISTS scrape_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id               UUID REFERENCES scrape_targets(id),
    site_name               TEXT NOT NULL,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    status                  TEXT NOT NULL DEFAULT 'running',  -- running, success, partial, failed
    items_found             INTEGER DEFAULT 0,
    items_new               INTEGER DEFAULT 0,
    items_updated           INTEGER DEFAULT 0,
    final_prices_harvested  INTEGER DEFAULT 0,
    error_message           TEXT,
    duration_ms             INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scrape_runs_target ON scrape_runs(target_id);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_site ON scrape_runs(site_name);
```

Tables auto-created on first API call (same pattern as conversations/evidence).

### Initial seed data

Pre-populate `scrape_targets` for the 13 known sources:

| name | scraper_type | schedule_cron | url |
|------|-------------|---------------|-----|
| machinio | scrapekit | 0 */6 * * * | https://www.machinio.com |
| ritchiebros | scrapekit | 0 */6 * * * | https://www.ritchiebros.com |
| surplusrecord | scrapekit | 0 */12 * * * | https://www.surplusrecord.com |
| energyauctions | scrapekit | 0 */12 * * * | https://www.energyauctions.com |
| allsurplus | scrapekit | 0 */12 * * * | https://www.allsurplus.com |
| ironplanet | scrapekit | 0 */12 * * * | https://www.ironplanet.com |
| govdeals | scrapekit | 0 */12 * * * | https://www.govdeals.com |
| bidspotter | scrapekit | 0 */6 * * * | https://www.bidspotter.com |
| equipmenttrader | scrapekit | 0 */6 * * * | https://www.equipmenttrader.com |
| kijiji | scrapekit | 0 */6 * * * | https://www.kijiji.ca |
| reflowx | standalone | 0 */6 * * * | https://www.reflowx.com |
| ironhub | standalone | 0 0 * * * | https://www.ironhub.com |
| fuelled | standalone | 0 */6 * * * | https://www.fuelled.com |
| sold_price_harvester | harvester | 0 2 * * * | — |

---

## Nova Backend — API Endpoints

All admin-only (JWT required). Modify existing `backend/app/api/admin_scrapers.py`.

### Scraper Targets

**GET /api/admin/scrapers** (upgrade existing)
Returns all targets with latest run info, listing counts from DB.

**POST /api/admin/scrapers**
Create new scraper target.
```json
{"name": "newsource", "url": "https://example.com", "scraper_type": "scrapekit", "schedule_cron": "0 */6 * * *"}
```

**PUT /api/admin/scrapers/{target_id}**
Update target (name, url, schedule_cron, status).

**DELETE /api/admin/scrapers/{target_id}**
Remove target. Does not delete listings from that source.

**POST /api/admin/scrapers/{target_id}/run**
Trigger immediate run. Sets `run_requested_at = NOW()` in DB. Also sends webhook to Proxmox runner via Tailscale: `POST $SCRAPER_RUNNER_URL/run/{name}`.

**POST /api/admin/scrapers/{target_id}/pause**
Sets `status = 'paused'`.

**POST /api/admin/scrapers/{target_id}/resume**
Sets `status = 'active'`.

### Scrape Runs

**GET /api/admin/scrapers/{target_id}/runs**
Run history for a target (last 20).

**GET /api/admin/scrapers/runs/recent**
Last 20 runs across all targets.

### Harvest

**POST /api/admin/scrapers/harvest**
Trigger sold price harvest via Tailscale webhook.

**GET /api/admin/scrapers/harvest/stats**
```json
{
  "total_closed_auctions": 8200,
  "harvested": 0,
  "remaining": 8200,
  "sources": {"bidspotter": 7079, "govdeals": 998, "ritchiebros": 180}
}
```

### Environment Variable

`SCRAPER_RUNNER_URL` — Proxmox Tailscale IP + port (e.g., `http://100.64.0.5:8200`)

---

## Nova Frontend — Scrapers Page Upgrade

Upgrade existing `frontend/nova-app/app/(app)/scrapers/page.tsx`.

### Metric Cards Row
- **Active Scrapers**: count where status = 'active'
- **Total Listings**: sum across all sources
- **With Pricing**: listings with asking_price > 0 OR final_price > 0
- **Last Refresh**: most recent scrape_run timestamp
- **Errors**: scrapers with health_pct < 50

### Scraper Table
Headers: SOURCE | TYPE | LISTINGS | WITH PRICE | SCHEDULE | LAST RUN | STATUS | ACTIONS

Each row:
- Source name + URL link
- Type badge (scrapekit / standalone / harvester)
- Listing count + with-price count
- Human-readable schedule ("Every 6h", "Daily", "Manual")
- Last run timestamp + duration
- Status dot (green/amber/red based on health_pct)
- Actions: **Run Now** button, **Pause/Resume** toggle

### Expandable Row Details
Click a row to expand:
- URL, schedule_cron, health_pct, scraper_type
- Last 5 runs table (date, items found, new, updated, status, duration, error)
- Edit schedule inline

### Add Scraper Modal
Button: "Add Scraper Target"
Fields: name, URL, scraper_type (dropdown), schedule (dropdown presets or custom cron)

### Sold Price Harvester Section
Below the scraper table:
- Card showing: closed auctions count, harvested count, remaining
- "Harvest Now" button
- Last harvest run timestamp + results

---

## Proxmox Scraper Runner

Standalone FastAPI app deployed on Proxmox, listening on Tailscale interface.

### File Structure
```
proxmox-scraper-runner/
├── runner.py          # FastAPI app — /run, /harvest, /health endpoints
├── scheduler.py       # Reads scrape_targets, runs due scrapers, updates scrape_runs
├── harvester.py       # Sold price harvester — re-visits closed auctions
├── requirements.txt   # fastapi, uvicorn, psycopg2-binary, httpx
├── .env               # DATABASE_URL (Railway public URL), SCRAPEKIT_PATH
└── systemd/
    └── scraper-runner.service  # systemd unit for the FastAPI listener
```

### Endpoints

**POST /run/{name}**
Runs the named scraper immediately. Looks up scraper_type from scrape_targets:
- `scrapekit` → calls `scrapekit/scripts/scrape_and_load.py {name}`
- `standalone` → calls the appropriate V1 script (reflowx, ironhub, fuelled)
Creates a `scrape_run` entry, updates `scrape_targets.last_run_at`.

**POST /run/all**
Runs all active targets.

**POST /harvest**
Runs sold price harvester.

**GET /health**
Returns runner status, last run time, tailscale connectivity.

### Scheduler (cron)

Runs every 15 minutes via cron:
```bash
*/15 * * * * cd /opt/scraper-runner && python scheduler.py
```

Logic:
1. Query `scrape_targets WHERE status = 'active'`
2. For each target: check if `run_requested_at IS NOT NULL` (on-demand) OR cron schedule is due
3. Run the scraper
4. Write `scrape_run` entry
5. Update `scrape_targets.last_run_at`, clear `run_requested_at`, update `health_pct`

### Sold Price Harvester

Runs daily at 2 AM (or on-demand):

```sql
SELECT id, source, url, external_id 
FROM listings 
WHERE auction_end < NOW() 
  AND auction_end > NOW() - INTERVAL '90 days'
  AND final_price IS NULL 
  AND source IN ('bidspotter', 'govdeals', 'ritchiebros', 'allsurplus')
ORDER BY auction_end DESC
LIMIT 200
```

For each listing:
1. Fetch the URL
2. Parse the sold/realized price (source-specific parser)
3. Update `listings.final_price`
4. Log count in `scrape_runs.final_prices_harvested`

Source-specific parsers extend the existing scrapekit scrapers — each already knows how to parse the site, we add a `parse_sold_price(html) -> float | None` method.

---

## Railway Tailscale Setup

Add Tailscale to the Railway backend as a sidecar service:

1. Create a Tailscale auth key (reusable, ephemeral) at `login.tailscale.com/admin/settings/keys`
2. Add env var `TAILSCALE_AUTHKEY` to a Tailscale sidecar service on Railway
3. The sidecar joins the tailnet, making the backend container accessible to Proxmox and vice versa
4. Nova backend uses `SCRAPER_RUNNER_URL` to reach Proxmox

Alternative (simpler): Don't run Tailscale on Railway. The Nova backend sets `run_requested_at` in the DB, and Proxmox cron picks it up within 15 minutes. "Run Now" has a 15-minute delay but requires zero networking setup.

**Recommendation:** Start with the DB-polling approach (no Tailscale on Railway). Add Tailscale later if instant triggering becomes important. This keeps the initial build simpler.

---

## What We're NOT Building

- No scraper code in the Nova app — execution stays on Proxmox
- No real-time scraper output streaming — check run history after completion
- No scraper code editor in the UI — scrapers are managed as code in scrapekit
- No automatic new-site onboarding — add scrapers via the UI, but writing the scraper code is manual

---

## Test Plan

### Unit Tests (Backend)

| # | Test | Expected |
|---|------|----------|
| 1 | Table auto-creation | scrape_targets + scrape_runs created on first API call |
| 2 | Create target | POST /admin/scrapers returns new target with UUID |
| 3 | List targets | GET /admin/scrapers returns all targets with listing counts |
| 4 | Update target | PUT /admin/scrapers/{id} changes schedule |
| 5 | Delete target | DELETE /admin/scrapers/{id} removes target |
| 6 | Pause/Resume | POST /admin/scrapers/{id}/pause sets status=paused |
| 7 | Run Now | POST /admin/scrapers/{id}/run sets run_requested_at |
| 8 | Run history | GET /admin/scrapers/{id}/runs returns last 20 runs |
| 9 | Harvest stats | GET /admin/scrapers/harvest/stats returns auction counts |
| 10 | Auth required | All endpoints return 401 without token |

### Frontend Tests (Manual)

| # | Test | Expected |
|---|------|----------|
| 1 | Page loads with targets | Scraper table shows all 14 targets |
| 2 | Add scraper | Modal → fill form → new target appears in table |
| 3 | Pause scraper | Click pause → status changes to paused → dot turns amber |
| 4 | Resume scraper | Click resume → status back to active → dot turns green |
| 5 | Run Now | Click Run Now → run_requested_at set → feedback shown |
| 6 | View run history | Expand row → last 5 runs shown with stats |
| 7 | Edit schedule | Change schedule inline → saves |
| 8 | Harvest stats | Harvest section shows auction counts |
| 9 | Delete scraper | Confirm → target removed from table |

### Integration Tests

| # | Test | Expected |
|---|------|----------|
| 1 | Proxmox runner health | GET /health returns OK |
| 2 | Trigger run from Nova | POST /run/machinio → scrape_run created in DB |
| 3 | Scheduler picks up due target | Set next_run_at to past → scheduler runs it |
| 4 | Harvester finds closed auctions | Query returns listings with auction_end < now() |

---

## Success Criteria

1. **All 14 scraper targets** visible in the management page with real run data
2. **CRUD works** — add, edit, pause, resume, delete targets from UI
3. **Run Now works** — triggers scraper within 15 minutes (DB polling) or instantly (Tailscale)
4. **Run history visible** — see when each scraper last ran, what it found, errors
5. **Sold price harvester** captures final_price on closed auctions
6. **Proxmox connects** to Railway Postgres via public URL
7. **Scrapekit + standalone scrapers** both execute correctly from the runner

---

## Implementation Order

1. **Database tables + seed data** — scrape_targets, scrape_runs, initial 14 targets
2. **Backend API** — CRUD endpoints, upgrade existing scrapers endpoint
3. **Frontend** — upgrade scrapers page with full management UI
4. **Proxmox runner** — FastAPI app + scheduler + cron setup
5. **Sold price harvester** — harvester logic + source-specific parsers
6. **Tailscale** (optional) — Railway sidecar for instant triggering
