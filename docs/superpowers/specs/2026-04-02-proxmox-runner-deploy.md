# Proxmox Scraper Runner — Deployment Spec
**Date:** April 2, 2026
**Status:** Approved
**Depends on:** scraper-management-design.md

---

## What This Is

A lightweight FastAPI app on your Proxmox server that:
1. Runs scrapers (scrapekit + standalone) on schedule
2. Runs the sold price harvester
3. Accepts webhook triggers from Nova (via Tailscale)
4. Writes results to Railway PostgreSQL

---

## Proxmox Setup

### Prerequisites
- Proxmox VM or LXC container with Python 3.11+
- Tailscale installed and joined to your tailnet
- Network access to Railway Postgres public URL
- Git access to clone scrapekit repo

### Directory Structure
```
/opt/scraper-runner/
├── runner.py              # FastAPI app (webhook listener)
├── scheduler.py           # Cron entrypoint — runs due scrapers
├── harvester.py           # Sold price harvester logic
├── parsers/               # Source-specific sold price parsers
│   ├── bidspotter.py
│   ├── govdeals.py
│   ├── ritchiebros.py
│   └── allsurplus.py
├── requirements.txt
├── .env
└── logs/
    └── runner.log

/opt/scrapekit/            # Clone of scrapekit repo
└── (existing scrapekit code)

/opt/nova-scripts/         # Clone of V1 standalone scrapers
├── scrape_reflowx.py
├── scrape_ironhub.py
└── scrape_fuelled_algolia.py
```

### Environment (.env)
```bash
DATABASE_URL=postgresql://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway
SCRAPEKIT_PATH=/opt/scrapekit
NOVA_SCRIPTS_PATH=/opt/nova-scripts
LOG_LEVEL=INFO
```

---

## runner.py — Webhook Listener

FastAPI app listening on `0.0.0.0:8200` (Tailscale only).

```python
# ~80 lines
from fastapi import FastAPI, BackgroundTasks
import subprocess, os, logging

app = FastAPI(title="Scraper Runner")

SCRAPEKIT = os.environ.get("SCRAPEKIT_PATH", "/opt/scrapekit")
SCRIPTS = os.environ.get("NOVA_SCRIPTS_PATH", "/opt/nova-scripts")
DB_URL = os.environ["DATABASE_URL"]

@app.get("/health")
async def health():
    return {"status": "ok", "tailscale": True}

@app.post("/run/{name}")
async def run_scraper(name: str, background: BackgroundTasks):
    """Trigger a named scraper. Returns immediately, runs in background."""
    background.add_task(_execute_scraper, name)
    return {"status": "queued", "scraper": name}

@app.post("/run/all")
async def run_all(background: BackgroundTasks):
    background.add_task(_execute_all)
    return {"status": "queued"}

@app.post("/harvest")
async def harvest(background: BackgroundTasks):
    background.add_task(_execute_harvest)
    return {"status": "queued"}
```

Execution logic:
- **scrapekit targets**: `subprocess.run(["python", "scripts/scrape_and_load.py", name], cwd=SCRAPEKIT, env={...DATABASE_URL...})`
- **standalone targets**: `subprocess.run(["python3", f"scrape_{name}.py"], cwd=SCRIPTS, env={...DATABASE_URL...})`
- **harvester**: calls `harvester.py` directly

Each execution:
1. Creates a `scrape_runs` row (status=running)
2. Runs the scraper subprocess
3. Updates `scrape_runs` (status, items, duration, error)
4. Updates `scrape_targets` (last_run_at, health_pct, total_items)

---

## scheduler.py — Cron Entrypoint

Runs every 15 minutes via cron. Checks what's due.

```python
# ~60 lines
"""Read scrape_targets, run due scrapers."""
import psycopg2, subprocess, croniter, datetime

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Check for on-demand requests (run_requested_at IS NOT NULL)
    cur.execute("""
        SELECT id, name, scraper_type 
        FROM scrape_targets 
        WHERE run_requested_at IS NOT NULL AND status = 'active'
    """)
    for target_id, name, stype in cur.fetchall():
        run_scraper(name, stype, target_id, conn)
        cur.execute("UPDATE scrape_targets SET run_requested_at = NULL WHERE id = %s", (target_id,))
        conn.commit()
    
    # 2. Check cron schedules
    cur.execute("""
        SELECT id, name, scraper_type, schedule_cron, last_run_at
        FROM scrape_targets 
        WHERE status = 'active' AND schedule_cron IS NOT NULL
    """)
    for target_id, name, stype, cron, last_run in cur.fetchall():
        if is_due(cron, last_run, now):
            run_scraper(name, stype, target_id, conn)
    
    conn.close()

def is_due(cron_expr, last_run, now):
    """Check if cron schedule is due since last run."""
    cron = croniter.croniter(cron_expr, last_run or now - datetime.timedelta(days=1))
    next_run = cron.get_next(datetime.datetime)
    return next_run <= now
```

---

## harvester.py — Sold Price Harvester

```python
# ~100 lines
"""Re-visit closed auctions to capture final/sold prices."""
import psycopg2, httpx, logging
from parsers import bidspotter, govdeals, ritchiebros, allsurplus

PARSERS = {
    "bidspotter": bidspotter.parse_sold_price,
    "govdeals": govdeals.parse_sold_price,
    "ritchiebros": ritchiebros.parse_sold_price,
    "allsurplus": allsurplus.parse_sold_price,
}

def harvest(limit=200):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, source, url 
        FROM listings 
        WHERE auction_end < NOW() 
          AND auction_end > NOW() - INTERVAL '90 days'
          AND final_price IS NULL 
          AND source IN ('bidspotter', 'govdeals', 'ritchiebros', 'allsurplus')
        ORDER BY auction_end DESC
        LIMIT %s
    """, (limit,))
    
    harvested = 0
    for listing_id, source, url in cur.fetchall():
        parser = PARSERS.get(source)
        if not parser or not url:
            continue
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            price = parser(resp.text)
            if price and price > 0:
                cur.execute("UPDATE listings SET final_price = %s WHERE id = %s", (price, listing_id))
                harvested += 1
        except Exception as e:
            logging.warning(f"Harvest failed for {source} {url}: {e}")
    
    conn.commit()
    conn.close()
    return harvested
```

### Source Parsers

Each parser is a single function: `parse_sold_price(html: str) -> float | None`

These need to be written by examining the closed auction pages for each site. Start with the highest-volume sources:

1. **BidSpotter** (7K closed) — Look for "Sold for", "Winning bid", or "Hammer price" in the page
2. **GovDeals** (1K closed) — Look for "Sold" or "Award Amount"
3. **Ritchie Bros** (180 closed) — Look for "Sold" price in results
4. **AllSurplus** (365 items) — Look for "Sold for" or final bid

These parsers will need iteration — run against a sample of URLs, check what the page looks like, refine the selectors.

---

## Systemd Service

```ini
# /etc/systemd/system/scraper-runner.service
[Unit]
Description=Fuelled Scraper Runner
After=network.target tailscaled.service

[Service]
Type=simple
User=scraper
WorkingDirectory=/opt/scraper-runner
EnvironmentFile=/opt/scraper-runner/.env
ExecStart=/opt/scraper-runner/.venv/bin/uvicorn runner:app --host 0.0.0.0 --port 8200
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable scraper-runner
sudo systemctl start scraper-runner
```

---

## Cron Setup

```bash
# /etc/cron.d/scraper-scheduler
*/15 * * * * scraper cd /opt/scraper-runner && /opt/scraper-runner/.venv/bin/python scheduler.py >> /opt/scraper-runner/logs/scheduler.log 2>&1

# Sold price harvester — daily at 2 AM
0 2 * * * scraper cd /opt/scraper-runner && /opt/scraper-runner/.venv/bin/python -c "from harvester import harvest; print(f'Harvested: {harvest()}')" >> /opt/scraper-runner/logs/harvester.log 2>&1
```

---

## Deployment Steps

1. **Create VM/container on Proxmox** — Ubuntu 22.04, 2GB RAM, 20GB disk
2. **Install prerequisites**: `apt install python3.11 python3.11-venv git`
3. **Install Tailscale**: `curl -fsSL https://tailscale.com/install.sh | sh && tailscale up`
4. **Clone repos**:
   ```bash
   git clone https://github.com/yetibeast/scrapekit.git /opt/scrapekit
   cp -r /path/to/fuelled-nova/scripts /opt/nova-scripts
   ```
5. **Set up runner**:
   ```bash
   mkdir -p /opt/scraper-runner/logs /opt/scraper-runner/parsers
   cd /opt/scraper-runner
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install fastapi uvicorn psycopg2-binary httpx croniter
   pip install -e /opt/scrapekit
   ```
6. **Configure .env** with Railway DATABASE_URL
7. **Install systemd service + cron**
8. **Test**: `curl http://localhost:8200/health`
9. **Test from Nova**: `curl http://100.x.x.x:8200/health` (Tailscale IP)

---

## Verification

| Test | Command | Expected |
|------|---------|----------|
| Runner health | `curl http://100.x.x.x:8200/health` | `{"status": "ok"}` |
| Trigger machinio | `curl -X POST http://100.x.x.x:8200/run/machinio` | `{"status": "queued"}` |
| Check DB after run | `SELECT * FROM scrape_runs ORDER BY started_at DESC LIMIT 1` | New row with items_found > 0 |
| Scheduler dry run | `python scheduler.py` | Picks up due targets |
| Harvester test | `python -c "from harvester import harvest; harvest(limit=5)"` | Attempts to harvest 5 URLs |
