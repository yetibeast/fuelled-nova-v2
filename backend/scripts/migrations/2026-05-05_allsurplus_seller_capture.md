# 2026-05-05 — AllSurplus seller-capture rollout

Companion plan for `2026-05-05_add_seller_fields_to_listings.sql`. The scraper
itself lives on the Proxmox runner, not in this repo, so the changes there
are deployed manually after this PR merges.

## Backend (this PR)

- New columns on `listings`: `seller_source_id`, `seller_name`,
  `seller_account_type`, `seller_other_assets_url` (all nullable + a partial
  index on `(source, seller_source_id)`).
- New endpoints:
  - `GET /api/admin/supply-targets` — per-(source, seller_source_id) aggregate.
  - `GET /api/admin/supply-targets/{source}/{seller_source_id}/listings` — drilldown.

## Proxmox scraper changes (deploy after this PR merges)

File: `/opt/scrapekit/scrapers/allsurplus.py` on the Proxmox runner
(`100.68.229.127`, deploy via `ssh -i ~/.ssh/id_arcanos root@…`).

### 1. Extract `seller_source_id` from every URL

The path `/asset/{seller_id}/{asset_id}` always carries the seller ID,
even when the public listing page hides the seller name. Capture it from
the URL during card parsing so 100% of listings get the ID:

```python
def _seller_id_from_url(url: str) -> str | None:
    m = re.search(r"/asset/(\d+)/\d+", url)
    return m.group(1) if m else None
```

Add `"seller_source_id": _seller_id_from_url(full_url)` to each item in
`_parse_listing_page`.

### 2. Parse `#seller_information` on detail pages

Public sellers (Commercial accounts mostly) expose a `<div id="seller_information">`
block with seller name, account type, and an "other assets" link. Add to
`_parse_detail_page`:

```python
info = soup.select_one("#seller_information")
if info:
    text = info.get_text(" ", strip=True)
    m = re.search(r"Seller:\s*([^[]+?)\s*\[", text)
    if m:
        result["seller_name"] = m.group(1).strip()
    m = re.search(r"Account Type:\s*(\w+)", text)
    if m:
        result["seller_account_type"] = m.group(1).strip()
    link = info.select_one('a[href]')
    if link and "other" in link.get_text(strip=True).lower():
        href = link["href"]
        result["seller_other_assets_url"] = (
            href if href.startswith("http")
            else f"https://www.allsurplus.com{href}"
        )
```

### 3. Surface fields through `normalize`

Add to the dict returned by `normalize`:

```python
"seller_source_id": raw.get("seller_source_id"),
"seller_name": raw.get("seller_name"),
"seller_account_type": raw.get("seller_account_type"),
"seller_other_assets_url": raw.get("seller_other_assets_url"),
```

### 4. Confirm `base.py` upserts the new fields

`/opt/scrapekit/scrapers/base.py` builds the INSERT … ON CONFLICT statement
from the keys returned by each scraper's `normalize`. If it uses an explicit
column list, append the four new keys there too. Verify with one record after
deploy.

### 5. Backfill across the existing 620 listings

`DETAIL_LIMIT = 30` in `allsurplus.py` caps how many detail pages get parsed
per run. For a one-time backfill: bump to `DETAIL_LIMIT = 700`, trigger
`POST http://100.68.229.127:8200/run/allsurplus`, watch it finish (each
detail page is ~7s + 2s sleep, so ~1.5–2h end-to-end), then revert
`DETAIL_LIMIT` back to `30` and restart `scraper-runner`.

Confirm via:
```sql
SELECT
  COUNT(*)                             AS total,
  COUNT(seller_source_id)              AS with_seller_id,
  COUNT(seller_name)                   AS with_seller_name
FROM listings
WHERE source = 'allsurplus';
```

## Phase 2 (later, deferred)

Authenticated capture for seller email contact — needs an AllSurplus account,
session-cookie persistence in the runner, and a monthly cookie refresh job.
Build only after Mark confirms Phase 1 output isn't sufficient for outreach.
