# Sold Price Harvester Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a harvester that re-visits closed auction listing URLs to capture final/sold prices, filling the `final_price` column on the `listings` table. Priority sources: AllSurplus, BidSpotter, GovDeals, Ritchie Bros.

**Architecture:** A standalone `harvester.py` script that lives alongside the scrapekit scrapers. Queries the DB for closed auction listings missing `final_price`, groups by source, dispatches to per-source parser functions that re-fetch the listing URL and extract the sold price. Runs on the Proxmox runner via cron (daily 2 AM) or on-demand via Nova API webhook. Each source parser is a separate file for isolation.

**Tech Stack:** Python 3, crawl4ai (AsyncWebCrawler), BeautifulSoup, asyncpg (direct DB access), same stack as existing scrapekit scrapers.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `scrapekit/harvester/harvester.py` | Main orchestrator: query DB, dispatch to parsers, batch update |
| Create | `scrapekit/harvester/parsers/allsurplus.py` | AllSurplus sold price extraction |
| Create | `scrapekit/harvester/parsers/bidspotter.py` | BidSpotter sold price extraction |
| Create | `scrapekit/harvester/parsers/govdeals.py` | GovDeals sold price extraction |
| Create | `scrapekit/harvester/parsers/ritchiebros.py` | Ritchie Bros sold price extraction |
| Create | `scrapekit/harvester/parsers/__init__.py` | Parser registry |
| Modify | DB (migration) | `ALTER TABLE listings ADD COLUMN IF NOT EXISTS final_price REAL` |

**Note:** The scrapekit project is at `/Users/lynch/Documents/projects/scrapekit/`. The harvester lives there because it shares DB access and crawl4ai patterns with the scrapers.

---

## Chunk 1: DB Migration + Harvester Skeleton

### Task 1: Add final_price column to listings

**Files:**
- Modify: DB schema via SQL

- [ ] **Step 1: Run ALTER TABLE**

```bash
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://fuelled:fuelled@localhost:5432/fuelled" \
  -c "ALTER TABLE listings ADD COLUMN IF NOT EXISTS final_price REAL;"
```

Expected: `ALTER TABLE` (idempotent, safe to re-run).

- [ ] **Step 2: Verify column exists**

```bash
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://fuelled:fuelled@localhost:5432/fuelled" \
  -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='listings' AND column_name='final_price';"
```

Expected: One row showing `final_price | real`.

- [ ] **Step 3: Check auction data baseline**

```bash
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://fuelled:fuelled@localhost:5432/fuelled" \
  -c "SELECT source, COUNT(*) AS total, COUNT(auction_end) AS with_auction_end, COUNT(final_price) AS with_final_price FROM listings WHERE source IN ('allsurplus','bidspotter','govdeals','ritchiebros','energyauctions','ironplanet') GROUP BY source ORDER BY total DESC;"
```

This tells us exactly how many listings per source have auction_end dates and need harvesting.

---

### Task 2: Harvester orchestrator

**Files:**
- Create: `scrapekit/harvester/__init__.py` (empty)
- Create: `scrapekit/harvester/parsers/__init__.py` (parser registry)
- Create: `scrapekit/harvester/harvester.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /Users/lynch/Documents/projects/scrapekit/harvester/parsers
touch /Users/lynch/Documents/projects/scrapekit/harvester/__init__.py
```

- [ ] **Step 2: Create parser registry**

```python
# scrapekit/harvester/parsers/__init__.py
"""Parser registry — maps source name to harvest function."""

from typing import Callable, Awaitable

# Each parser: async def harvest(url: str) -> float | None
ParserFn = Callable[[str], Awaitable[float | None]]

_PARSERS: dict[str, ParserFn] = {}

def register(source: str):
    """Decorator to register a harvest parser for a source."""
    def wrapper(fn: ParserFn) -> ParserFn:
        _PARSERS[source] = fn
        return fn
    return wrapper

def get_parser(source: str) -> ParserFn | None:
    return _PARSERS.get(source)

def available_sources() -> list[str]:
    return list(_PARSERS.keys())
```

- [ ] **Step 3: Create main harvester**

```python
# scrapekit/harvester/harvester.py
"""Sold price harvester — re-visits closed auction URLs to capture final prices."""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import asyncpg

# Import parsers to trigger registration
from harvester.parsers import get_parser, available_sources
from harvester.parsers import allsurplus, bidspotter, govdeals, ritchiebros  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("harvester")

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://fuelled:fuelled@localhost:5432/fuelled"
)

BATCH_SIZE = 50  # Listings per source per run (avoid hammering sites)


async def fetch_candidates(pool: asyncpg.Pool, source: str, limit: int) -> list[dict]:
    """Get closed auction listings missing final_price for a given source."""
    rows = await pool.fetch("""
        SELECT id, url, source, title, current_bid, auction_end
        FROM listings
        WHERE source = $1
          AND auction_end IS NOT NULL
          AND final_price IS NULL
          AND url IS NOT NULL
        ORDER BY auction_end DESC
        LIMIT $2
    """, source, limit)
    return [dict(r) for r in rows]


async def update_final_price(pool: asyncpg.Pool, listing_id: int, price: float):
    """Set final_price on a listing."""
    await pool.execute(
        "UPDATE listings SET final_price = $1 WHERE id = $2",
        price, listing_id
    )


async def run_harvest(sources: list[str] | None = None, batch_size: int = BATCH_SIZE):
    """Main harvest loop."""
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)

    try:
        targets = sources or available_sources()
        log.info("Harvesting sources: %s (batch=%d)", targets, batch_size)

        total_harvested = 0
        total_errors = 0

        for source in targets:
            parser = get_parser(source)
            if not parser:
                log.warning("No parser for source: %s", source)
                continue

            candidates = await fetch_candidates(pool, source, batch_size)
            if not candidates:
                log.info("[%s] No candidates to harvest", source)
                continue

            log.info("[%s] Processing %d candidates", source, len(candidates))
            harvested = 0
            errors = 0

            for listing in candidates:
                try:
                    price = await parser(listing["url"])
                    if price and price > 0:
                        await update_final_price(pool, listing["id"], price)
                        harvested += 1
                        log.debug("[%s] %s -> $%.2f", source, listing["title"][:50], price)
                    else:
                        log.debug("[%s] No price found: %s", source, listing["url"])
                except Exception as exc:
                    errors += 1
                    log.warning("[%s] Error harvesting %s: %s", source, listing["url"], exc)

                # Polite delay between requests
                await asyncio.sleep(1.5)

            log.info("[%s] Harvested %d/%d (errors: %d)", source, harvested, len(candidates), errors)
            total_harvested += harvested
            total_errors += errors

        log.info("Harvest complete: %d prices captured, %d errors", total_harvested, total_errors)
        return {"harvested": total_harvested, "errors": total_errors}
    finally:
        await pool.close()


if __name__ == "__main__":
    # CLI: python -m harvester.harvester [source1 source2 ...]
    sources = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(run_harvest(sources=sources))
```

- [ ] **Step 4: Verify imports work**

```bash
cd /Users/lynch/Documents/projects/scrapekit && python3 -c "from harvester.parsers import available_sources; print(available_sources())"
```

Expected: `[]` (no parsers registered yet)

- [ ] **Step 5: Commit**

```bash
cd /Users/lynch/Documents/projects/scrapekit
git add harvester/
git commit -m "feat: harvester skeleton with orchestrator and parser registry"
```

---

## Chunk 2: Source Parsers

### Task 3: AllSurplus parser

AllSurplus is a timed auction site. Closed lots typically show "Sold" or "Winning Bid" on the detail page. Uses crawl4ai to fetch the page and BeautifulSoup to extract the price.

**Files:**
- Create: `scrapekit/harvester/parsers/allsurplus.py`

- [ ] **Step 1: Create parser**

```python
# scrapekit/harvester/parsers/allsurplus.py
"""AllSurplus sold price parser."""

import re
import logging
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from harvester.parsers import register

log = logging.getLogger("harvester.allsurplus")


def _extract_price(html: str) -> float | None:
    """Extract sold/winning price from AllSurplus lot page."""
    soup = BeautifulSoup(html, "html.parser")

    # Look for sold/winning bid indicators
    for pattern in [
        # Common patterns on auction close pages
        soup.find(string=re.compile(r"(sold|winning bid|final bid|hammer price)", re.I)),
        soup.find(class_=re.compile(r"(sold|winning|final|closed)", re.I)),
    ]:
        if pattern:
            # Find nearest price-like text
            parent = pattern.parent if hasattr(pattern, "parent") else pattern
            if parent:
                text = parent.get_text() if hasattr(parent, "get_text") else str(parent)
                prices = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)
                if prices:
                    return float(prices[0].replace("$", "").replace(",", ""))

    # Fallback: look for any prominent price on a closed lot
    price_els = soup.find_all(class_=re.compile(r"price|bid|amount", re.I))
    for el in price_els:
        text = el.get_text(strip=True)
        match = re.search(r"\$?([\d,]+(?:\.\d{2})?)", text)
        if match:
            val = float(match.group(1).replace(",", ""))
            if val > 0:
                return val

    return None


@register("allsurplus")
async def harvest(url: str) -> float | None:
    """Fetch an AllSurplus lot page and extract the sold price."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.html:
                return _extract_price(result.html)
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
    return None
```

- [ ] **Step 2: Test with a real URL (manual)**

```bash
cd /Users/lynch/Documents/projects/scrapekit
# Find a closed AllSurplus listing URL
/opt/homebrew/opt/postgresql@16/bin/psql "postgresql://fuelled:fuelled@localhost:5432/fuelled" \
  -c "SELECT url FROM listings WHERE source='allsurplus' AND auction_end IS NOT NULL LIMIT 3;"
```

Then test the parser manually against one URL to verify extraction works.

- [ ] **Step 3: Commit**

```bash
git add harvester/parsers/allsurplus.py
git commit -m "feat: AllSurplus sold price parser"
```

---

### Task 4: BidSpotter parser

BidSpotter shows auction results with lot prices. Closed lots display the hammer price. BidSpotter has the highest volume (10,679 listings) so this is high-value.

**Files:**
- Create: `scrapekit/harvester/parsers/bidspotter.py`

- [ ] **Step 1: Create parser**

```python
# scrapekit/harvester/parsers/bidspotter.py
"""BidSpotter sold price parser."""

import re
import logging
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from harvester.parsers import register

log = logging.getLogger("harvester.bidspotter")


def _extract_price(html: str) -> float | None:
    """Extract sold price from BidSpotter lot page."""
    soup = BeautifulSoup(html, "html.parser")

    # BidSpotter shows "Sold for $X" or "Winning Bid: $X" on closed lots
    for text_pattern in [r"sold\s+for", r"winning\s+bid", r"hammer\s+price", r"final\s+bid"]:
        el = soup.find(string=re.compile(text_pattern, re.I))
        if el:
            context = el.parent.get_text() if el.parent else str(el)
            match = re.search(r"[\$£€]?\s*([\d,]+(?:\.\d{2})?)", context)
            if match:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    return val

    # Look for price in bid-related elements
    for selector in [
        {"class_": re.compile(r"sold|result|final", re.I)},
        {"id": re.compile(r"price|bid|result", re.I)},
        {"data-lot-price": True},
    ]:
        el = soup.find(**selector)
        if el:
            text = el.get_text(strip=True)
            match = re.search(r"[\$£€]?\s*([\d,]+(?:\.\d{2})?)", text)
            if match:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    return val

    return None


@register("bidspotter")
async def harvest(url: str) -> float | None:
    """Fetch a BidSpotter lot page and extract the sold price."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.html:
                return _extract_price(result.html)
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
    return None
```

- [ ] **Step 2: Test with a real URL (manual)**
- [ ] **Step 3: Commit**

```bash
git add harvester/parsers/bidspotter.py
git commit -m "feat: BidSpotter sold price parser"
```

---

### Task 5: GovDeals parser

GovDeals shows "Winning Bid" on closed auction pages. Government surplus — typically well-structured HTML.

**Files:**
- Create: `scrapekit/harvester/parsers/govdeals.py`

- [ ] **Step 1: Create parser**

```python
# scrapekit/harvester/parsers/govdeals.py
"""GovDeals sold price parser."""

import re
import logging
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from harvester.parsers import register

log = logging.getLogger("harvester.govdeals")


def _extract_price(html: str) -> float | None:
    """Extract winning bid from GovDeals lot page."""
    soup = BeautifulSoup(html, "html.parser")

    # GovDeals pattern: "Winning Bid: $X,XXX.XX" or "Current Bid: $X" on closed lots
    for pattern in [r"winning\s+bid", r"sold\s+for", r"final\s+bid", r"closed\s+at"]:
        el = soup.find(string=re.compile(pattern, re.I))
        if el:
            # Price is often in the next sibling or same parent
            parent = el.parent
            if parent:
                text = parent.get_text()
                match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
                if match:
                    return float(match.group(1).replace(",", ""))
            # Check next sibling
            next_el = el.find_next()
            if next_el:
                text = next_el.get_text()
                match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
                if match:
                    return float(match.group(1).replace(",", ""))

    # Fallback: structured data
    for el in soup.find_all(attrs={"data-price": True}):
        try:
            return float(el["data-price"])
        except (ValueError, KeyError):
            continue

    return None


@register("govdeals")
async def harvest(url: str) -> float | None:
    """Fetch a GovDeals lot page and extract the winning bid."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.html:
                return _extract_price(result.html)
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
    return None
```

- [ ] **Step 2: Test with a real URL (manual)**
- [ ] **Step 3: Commit**

```bash
git add harvester/parsers/govdeals.py
git commit -m "feat: GovDeals sold price parser"
```

---

### Task 6: Ritchie Bros parser

Ritchie Bros is the largest industrial auctioneer. Lower volume in our DB (180 listings) but high-quality comp data. May use JSON/API data embedded in pages.

**Files:**
- Create: `scrapekit/harvester/parsers/ritchiebros.py`

- [ ] **Step 1: Create parser**

```python
# scrapekit/harvester/parsers/ritchiebros.py
"""Ritchie Bros sold price parser."""

import json
import re
import logging
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from harvester.parsers import register

log = logging.getLogger("harvester.ritchiebros")


def _extract_price(html: str) -> float | None:
    """Extract sold price from Ritchie Bros lot page."""
    soup = BeautifulSoup(html, "html.parser")

    # Ritchie Bros often embeds JSON-LD or data attributes
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                price = data.get("price") or data.get("offers", {}).get("price")
                if price:
                    return float(str(price).replace(",", ""))
        except (json.JSONDecodeError, ValueError, AttributeError):
            continue

    # Look for "Sold" price text patterns
    for pattern in [r"sold\s*:?\s*\$", r"hammer\s+price", r"winning\s+bid", r"price\s+realized"]:
        el = soup.find(string=re.compile(pattern, re.I))
        if el:
            context = el.parent.get_text() if el.parent else str(el)
            match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", context)
            if match:
                return float(match.group(1).replace(",", ""))

    # Data attributes
    for attr in ["data-sold-price", "data-price", "data-hammer-price"]:
        el = soup.find(attrs={attr: True})
        if el:
            try:
                return float(el[attr].replace(",", ""))
            except (ValueError, KeyError):
                continue

    return None


@register("ritchiebros")
async def harvest(url: str) -> float | None:
    """Fetch a Ritchie Bros lot page and extract the sold price."""
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.html:
                return _extract_price(result.html)
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
    return None
```

- [ ] **Step 2: Test with a real URL (manual)**
- [ ] **Step 3: Commit**

```bash
git add harvester/parsers/ritchiebros.py
git commit -m "feat: Ritchie Bros sold price parser"
```

---

## Chunk 3: Integration + Deployment

### Task 7: Integration test script

**Files:**
- Create: `scrapekit/harvester/test_harvest.py`

- [ ] **Step 1: Create a dry-run test script**

```python
# scrapekit/harvester/test_harvest.py
"""Quick integration test — fetches 2 candidates per source, prints results without DB writes."""

import asyncio
import os
import asyncpg

from harvester.parsers import get_parser, available_sources
from harvester.parsers import allsurplus, bidspotter, govdeals, ritchiebros  # noqa: F401

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fuelled:fuelled@localhost:5432/fuelled")

async def test():
    pool = await asyncpg.create_pool(DATABASE_URL)
    try:
        for source in available_sources():
            parser = get_parser(source)
            rows = await pool.fetch("""
                SELECT id, url, title, current_bid, auction_end
                FROM listings
                WHERE source = $1 AND auction_end IS NOT NULL AND url IS NOT NULL
                LIMIT 2
            """, source)
            print(f"\n=== {source} ({len(rows)} candidates) ===")
            for r in rows:
                print(f"  URL: {r['url']}")
                print(f"  Title: {r['title'][:60]}")
                print(f"  Current bid: {r['current_bid']}")
                try:
                    price = await parser(r["url"])
                    print(f"  --> Harvested price: ${price:.2f}" if price else "  --> No price found")
                except Exception as e:
                    print(f"  --> ERROR: {e}")
                await asyncio.sleep(2)
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(test())
```

- [ ] **Step 2: Run dry test**

```bash
cd /Users/lynch/Documents/projects/scrapekit
DATABASE_URL="postgresql://fuelled:fuelled@localhost:5432/fuelled" python3 -m harvester.test_harvest
```

Review output: for each source, check if prices are being extracted. If a parser fails, inspect the actual HTML structure and adjust the extraction regex/selectors.

- [ ] **Step 3: Iterate on parsers based on test results**

Adjust `_extract_price()` functions based on actual page HTML. This is the critical tuning step — the regex patterns in the plan are educated guesses based on common auction site patterns. Real pages may differ.

- [ ] **Step 4: Commit**

```bash
git add harvester/
git commit -m "feat: harvester integration test + parser tuning"
```

---

### Task 8: Proxmox deployment prep

Document how to deploy the harvester to the Proxmox runner.

- [ ] **Step 1: Update runner docs**

Add to `docs/infrastructure/proxmox-scraper-runner.md`:
- Copy `scrapekit/harvester/` to `/opt/scraper-runner/harvester/` on LXC 107
- Ensure `crawl4ai`, `asyncpg`, `beautifulsoup4` are installed in runner venv
- Cron: `0 2 * * * cd /opt/scraper-runner && python3 -m harvester.harvester >> logs/harvester.log 2>&1`
- Manual: `python3 -m harvester.harvester allsurplus bidspotter` (specific sources)

- [ ] **Step 2: Commit**

```bash
git add docs/infrastructure/proxmox-scraper-runner.md
git commit -m "docs: harvester deployment instructions for Proxmox runner"
```

---

## Key Risks

1. **Auction sites remove closed listings** — URLs may 404 after 30-90 days. Harvest should run regularly to catch prices before pages expire.
2. **HTML structure varies** — Parser regex is best-guess. Step 3 of Task 7 (iteration) is critical. Expect 1-2 rounds of tuning per source.
3. **Rate limiting** — 1.5s delay between requests + batch_size=50 per source = ~75 seconds per source per run. Respectful pace.
4. **Bot detection** — Ritchie Bros and IronPlanet may block crawl4ai. May need headed browser or different user-agent. Start with the simpler sources.
