# Proxmox Scraper Runner — Operations Guide
**Last Updated:** April 2, 2026

---

## Overview

The scraper runner is a FastAPI application on a Proxmox LXC container that executes web scrapers on a schedule and writes results to the Railway PostgreSQL database. It runs 14 scraper targets across 12 sources plus a sold price harvester.

## Infrastructure

| Component | Details |
|-----------|---------|
| **Container** | Proxmox LXC 107 (`ubuntu`), Ubuntu 24.04, 10GB disk, 1GB RAM, 2 cores |
| **Local IP** | `10.0.0.98` |
| **Tailscale IP** | `100.68.229.127` |
| **Proxmox Node** | `yeti` |
| **Runner Port** | `8200` (FastAPI/uvicorn) |
| **Database** | Railway PostgreSQL: `trolley.proxy.rlwy.net:34278/railway` |

## File Structure

```
/opt/scraper-runner/
├── runner.py              # FastAPI app — webhook listener + scraper execution
├── scheduler.py           # Cron entrypoint — checks scrape_targets, runs due scrapers
├── harvester.py           # Sold price harvester — re-visits closed auctions
├── seed_targets.py        # Seeds initial 14 scrape targets
├── .env                   # DATABASE_URL + paths
├── .venv/                 # Python 3.12 virtual environment
├── logs/
│   ├── scheduler.log      # Cron scheduler output
│   └── harvester.log      # Harvester output
└── parsers/               # Source-specific sold price parsers (future)

/opt/scrapekit/            # Scrapekit framework (11 scrapers)
├── scrapers/              # allsurplus, bidspotter, energyauctions, equipmenttrader,
│                          # govdeals, ironplanet, kijiji, machinio, ritchiebros, surplusrecord
└── scripts/
    └── scrape_and_load.py # Main scrapekit entry point

/opt/nova-scripts/         # V1 standalone scrapers
├── scrape_reflowx.py      # ReflowX API scraper
├── scrape_ironhub.py      # IronHub (needs Cloudflare bypass)
└── scrape_fuelled_algolia.py  # Fuelled marketplace via Algolia
```

## Environment Variables (.env)

```bash
DATABASE_URL=postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway
SCRAPEKIT_PATH=/opt/scrapekit
NOVA_SCRIPTS_PATH=/opt/nova-scripts
LOG_LEVEL=INFO
```

## Services

### FastAPI Runner (systemd)

```bash
# Service file: /etc/systemd/system/scraper-runner.service
systemctl status scraper-runner     # Check status
systemctl restart scraper-runner    # Restart
systemctl stop scraper-runner       # Stop
journalctl -u scraper-runner -n 50  # View logs
```

### Cron Jobs (/etc/cron.d/scraper-scheduler)

```bash
# Scheduler — every 15 minutes, checks scrape_targets for due scrapers
*/15 * * * * root cd /opt/scraper-runner && /opt/scraper-runner/.venv/bin/python scheduler.py >> /opt/scraper-runner/logs/scheduler.log 2>&1

# Sold price harvester — daily at 2 AM
0 2 * * * root cd /opt/scraper-runner && /opt/scraper-runner/.venv/bin/python -c "from harvester import harvest; print(f'Harvested: {harvest()}')" >> /opt/scraper-runner/logs/harvester.log 2>&1
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Full status: runner, Tailscale, DB, targets, last run, listings |
| POST | `/run/{name}` | Trigger named scraper (e.g., `/run/machinio`) |
| POST | `/run-all` | Trigger all active scrapers |
| POST | `/harvest` | Trigger sold price harvester |

### Health Response Example

```json
{
    "status": "ok",
    "runner": "active",
    "tailscale_ip": "100.68.229.127",
    "db": "connected",
    "targets": { "active": 14 },
    "last_run": {
        "site": "machinio",
        "status": "success",
        "at": "2026-04-02T22:31:14+00:00",
        "new": 1,
        "found": 247
    },
    "listings": 40094
}
```

## Scraper Targets (14 total)

| Name | Type | Schedule | Source |
|------|------|----------|--------|
| machinio | scrapekit | Every 6h | machinio.com |
| ritchiebros | scrapekit | Every 6h | ritchiebros.com |
| bidspotter | scrapekit | Every 6h | bidspotter.com |
| equipmenttrader | scrapekit | Every 6h | equipmenttrader.com |
| kijiji | scrapekit | Every 6h | kijiji.ca |
| reflowx | standalone | Every 6h | reflowx.com |
| fuelled | standalone | Every 6h | fuelled.com |
| surplusrecord | scrapekit | Every 12h | surplusrecord.com |
| energyauctions | scrapekit | Every 12h | energyauctions.com |
| allsurplus | scrapekit | Every 12h | allsurplus.com |
| ironplanet | scrapekit | Every 12h | ironplanet.com |
| govdeals | scrapekit | Every 12h | govdeals.com |
| ironhub | standalone | Daily | ironhub.com (Cloudflare) |
| sold_price_harvester | harvester | Daily 2AM | Re-visits closed auctions |

## Database Tables

### scrape_targets
Stores scraper configuration. Managed via Nova UI or directly.

Key columns: `name`, `status` (active/paused/disabled), `scraper_type` (scrapekit/standalone/harvester), `schedule_cron`, `last_run_at`, `run_requested_at` (set by "Run Now"), `health_pct`, `total_items`

### scrape_runs
History of every scraper execution.

Key columns: `target_id`, `site_name`, `status` (running/success/partial/failed), `listings_new`, `listings_updated`, `listings_found`, `final_prices_harvested`, `error_message`, `duration_ms`

## How It Works

### Scheduled Runs (every 15 min)
1. Cron runs `scheduler.py`
2. Scheduler queries `scrape_targets` for on-demand requests (`run_requested_at IS NOT NULL`) and cron-due targets
3. For each due target, calls `runner._run_scraper(name)`
4. Runner executes the appropriate scraper (scrapekit subprocess or standalone script)
5. Creates `scrape_runs` entry, updates `scrape_targets` with results

### On-Demand Runs
1. Nova UI sets `run_requested_at` on the target
2. Next scheduler cycle (within 15 min) picks it up
3. OR direct webhook: `POST http://100.68.229.127:8200/run/{name}`

### Sold Price Harvester
1. Queries `listings` where `auction_end < NOW()` and `final_price IS NULL`
2. Re-visits each listing URL
3. Parses sold/realized price using regex patterns
4. Updates `final_price` on the listing

## Common Operations

```bash
# SSH into container
ssh -i ~/.ssh/id_arcanos root@10.0.0.98
# or via Tailscale:
ssh -i ~/.ssh/id_arcanos root@100.68.229.127

# Check runner health
curl http://100.68.229.127:8200/health

# Trigger a specific scraper
curl -X POST http://100.68.229.127:8200/run/machinio

# Trigger all scrapers
curl -X POST http://100.68.229.127:8200/run-all

# Trigger sold price harvest
curl -X POST http://100.68.229.127:8200/harvest

# View recent runs in DB
cd /opt/scraper-runner && source .venv/bin/activate
python3 -c "
import psycopg2, os
from dotenv import load_dotenv; load_dotenv('.env')
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT site_name, status, listings_new, listings_found, duration_ms FROM scrape_runs ORDER BY started_at DESC LIMIT 10')
for r in cur.fetchall():
    print(f'{r[0]}: {r[1]} — new={r[2]}, found={r[3]}, {r[4]}ms')
conn.close()
"

# Check scheduler log
tail -50 /opt/scraper-runner/logs/scheduler.log

# Check harvester log
tail -20 /opt/scraper-runner/logs/harvester.log

# Restart runner after changes
systemctl restart scraper-runner
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Container not reachable | `pct status 107` on yeti, `pct start 107` if stopped |
| Tailscale down | `ssh root@10.0.0.98`, then `systemctl start tailscaled && tailscale up` |
| Runner not starting | `journalctl -u scraper-runner -n 50` for errors |
| Playwright missing | `source /opt/scraper-runner/.venv/bin/activate && playwright install --with-deps chromium` |
| DB connection failed | Check `.env` DATABASE_URL, verify Railway Postgres is running |
| Scraper timing out | Check if site structure changed, review scrapekit scraper code |
| IronHub Cloudflare | Needs headed browser: `python3 /opt/nova-scripts/scrape_ironhub.py --headed --save-cookies` (manual) |

## Proxmox Container Config

Container 107 requires these special settings for Tailscale:

```
# /etc/pve/lxc/107.conf (on Proxmox host yeti)
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

Nesting must be enabled in container features.
