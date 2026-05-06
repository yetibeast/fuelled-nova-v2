"""Kijiji scraper - Canadian classifieds for Western Canada oilfield/industrial.

Next.js app with Apollo GraphQL state in __NEXT_DATA__.
40 items per page, pagination via /page-N/ in URL.
"""

import asyncio
import json
import math
import re

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from scrapers.base import BaseScraper

BASE = "https://www.kijiji.ca"
CATEGORY_SLUG = "heavy-equipment-machinery"
CATEGORY_ID = "c340"

# (province_slug, location_id)
PROVINCES = [
    ("alberta", "l9003"),
    ("saskatchewan", "l9009"),
    ("british-columbia", "l9007"),
]

# (keyword, max_pages) — 0 = scrape all pages
KEYWORDS = [
    ("generator", 0),
    ("compressor", 0),
    ("pump", 0),
    ("tank", 0),
    ("drilling", 0),
    ("oilfield", 0),
    ("industrial", 0),
    ("production", 0),
    ("excavator", 10),
    ("loader", 10),
    ("truck", 10),
    ("trailer", 10),
]


class KijijiScraper(BaseScraper):
    source = "kijiji"

    async def scrape(self) -> list[dict]:
        browser_config = BrowserConfig(headless=True, java_script_enabled=True)
        run_config = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=60000,
            delay_before_return_html=8.0,
        )

        all_items = {}

        async with AsyncWebCrawler(config=browser_config) as crawler:
            for prov_slug, loc_id in PROVINCES:
                for keyword, max_pages in KEYWORDS:
                    page = 1

                    while True:
                        if page == 1:
                            url = (
                                f"{BASE}/b-{CATEGORY_SLUG}/{prov_slug}/"
                                f"{keyword}/k0{CATEGORY_ID}{loc_id}"
                            )
                        else:
                            url = (
                                f"{BASE}/b-{CATEGORY_SLUG}/{prov_slug}/"
                                f"{keyword}/page-{page}/k0{CATEGORY_ID}{loc_id}"
                            )

                        label = f"{prov_slug}/{keyword} p{page}"
                        print(f"  [{label}]")

                        result = await crawler.arun(url=url, config=run_config)
                        if not result.success:
                            print(f"    Failed: {result.error_message}")
                            break

                        items, total_count = self._parse_listings(
                            result.html, keyword, prov_slug
                        )

                        new = 0
                        for item in items:
                            lid = item["listing_id"]
                            if lid not in all_items:
                                all_items[lid] = item
                                new += 1

                        print(f"    Found: {len(items)}, New: {new}")

                        if not items or new == 0:
                            break

                        total_pages = math.ceil(total_count / 40) if total_count else 1
                        effective_max = max_pages or total_pages
                        if page >= effective_max:
                            break

                        page += 1
                        await asyncio.sleep(2)

                    await asyncio.sleep(1)

        # Phase 2: enrich seller info from a sample of detail pages.
        # Search-page Apollo only carries posterId; detail pages have the full
        # CommercialProfileV2 (name, profilePath, websiteUrl). Fetch one detail
        # page per unique posterId so we don't hammer kijiji — broadcast the
        # dealer info to every listing that shares the posterId.
        seller_cache: dict[str, dict] = {}
        seen_poster_ids: set[str] = set()
        # Build "first listing per posterId" to use as the sampling probe
        probe_targets: list[dict] = []
        for item in all_items.values():
            pid = item.get("seller_source_id")
            if not pid or pid in seen_poster_ids:
                continue
            seen_poster_ids.add(pid)
            probe_targets.append(item)

        # Cap detail-fetches per run to limit run time + ToS exposure.
        # Over successive runs the union of probes converges on full coverage.
        DETAIL_LIMIT = 40
        probe_targets = probe_targets[:DETAIL_LIMIT]

        if probe_targets:
            print(f"  Phase 2: enriching {len(probe_targets)} unique seller profiles...")
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for i, item in enumerate(probe_targets, 1):
                    pid = item["seller_source_id"]
                    url = item.get("url") or ""
                    if url and not url.startswith("http"):
                        url = f"{BASE}{url}"
                    if not url:
                        continue
                    print(f"    [{i}/{len(probe_targets)}] {pid}")
                    try:
                        result = await crawler.arun(url=url, config=run_config)
                        if result.success:
                            seller = self._parse_detail_seller(result.html, pid)
                            if seller:
                                seller_cache[pid] = seller
                    except Exception as exc:
                        print(f"      enrichment failed: {exc}")
                    await asyncio.sleep(2)

            # Broadcast cached seller info to every listing in this scrape
            for item in all_items.values():
                pid = item.get("seller_source_id")
                if pid and pid in seller_cache:
                    for k, v in seller_cache[pid].items():
                        item.setdefault(k, v)

        print(f"  Total unique items: {len(all_items)}")
        return list(all_items.values())

    def _parse_detail_seller(self, html: str, poster_id: str) -> dict | None:
        """Pull CommercialProfileV2 from a kijiji detail page Apollo state.

        Returns dict with seller_name, seller_account_type, and (when present)
        seller_other_assets_url. Private sellers have no CommercialProfileV2
        entry — we still record account_type=Private from the StandardListing's
        posterInfo so the supply-targets endpoint shows them as anonymous.
        """
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html, re.DOTALL,
        )
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return None
        apollo = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})

        # Pull the StandardListing's posterInfo for sellerType
        seller_type = None
        for key, val in apollo.items():
            if not isinstance(val, dict):
                continue
            if key.startswith("StandardListing:") and val.get("posterInfo"):
                pi = val["posterInfo"]
                if pi.get("posterId") == poster_id or str(pi.get("posterId")) == str(poster_id):
                    seller_type = pi.get("sellerType")
                    break

        # Map COMMERCIAL/PRIVATE to friendlier "Dealer"/"Private"
        account_type = None
        if seller_type == "COMMERCIAL":
            account_type = "Dealer"
        elif seller_type == "PRIVATE":
            account_type = "Private"

        # CommercialProfileV2 entry has the dealer name + profile path
        profile_key = f"CommercialProfileV2:{poster_id}"
        profile = apollo.get(profile_key) or {}
        name = profile.get("name")
        profile_path = profile.get("profilePath")
        other_assets_url = (
            f"{BASE}{profile_path}" if profile_path and profile_path.startswith("/")
            else profile_path
        )

        # Skip empty payloads to avoid overwriting good data with nothing
        if not (name or account_type or other_assets_url):
            return None

        result = {}
        if name:
            result["seller_name"] = name
        if account_type:
            result["seller_account_type"] = account_type
        if other_assets_url:
            result["seller_other_assets_url"] = other_assets_url
        return result

    def _parse_listings(
        self, html: str, keyword: str, province: str
    ) -> tuple[list[dict], int]:
        """Extract listings from __NEXT_DATA__ Apollo state."""
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not m:
            return [], 0

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return [], 0

        apollo = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
        root = apollo.get("ROOT_QUERY", {})

        # Get total count from pagination
        total_count = 0
        for k, v in root.items():
            if "searchResultsPageByUrl" in k:
                total_count = v.get("pagination", {}).get("totalCount", 0)
                break

        # Extract StandardListing entries
        items = []
        for key, val in apollo.items():
            if not key.startswith("StandardListing:"):
                continue

            listing_id = val.get("id")
            title = val.get("title")
            if not listing_id or not title:
                continue

            # Price (amount is in cents)
            price_data = val.get("price") or {}
            price_cents = price_data.get("amount")
            price = price_cents / 100.0 if price_cents else None
            price_type = price_data.get("type", "")

            # Location
            loc_data = val.get("location", {})
            city = loc_data.get("name", "")
            address = loc_data.get("address", "")

            # Parse province from address
            prov_code = ""
            if address:
                prov_match = re.search(
                    r",\s*(AB|SK|BC|MB|ON|QC)\b", address
                )
                if prov_match:
                    prov_code = prov_match.group(1)

            # Images
            image_urls = val.get("imageUrls", [])
            image_url = image_urls[0] if image_urls else None

            # Attributes
            attrs = {}
            attr_list = (val.get("attributes") or {}).get("all", [])
            for attr in attr_list:
                name = attr.get("canonicalName", "")
                values = attr.get("canonicalValues", [])
                if values:
                    attrs[name] = values[0]

            year = None
            if attrs.get("caryear"):
                try:
                    year = int(attrs["caryear"])
                except ValueError:
                    pass

            hours = None
            if attrs.get("hours"):
                try:
                    hours = int(attrs["hours"])
                except ValueError:
                    pass

            # Stable per-seller ID from Apollo posterInfo. Lets us cluster
            # listings by dealer even before the Phase-2 detail enrichment runs
            # (full name + profile path lives on detail pages, not search).
            poster_info = val.get("posterInfo") or {}
            poster_id = poster_info.get("posterId")

            items.append(
                {
                    "listing_id": str(listing_id),
                    "title": title,
                    "description": val.get("description", ""),
                    "url": val.get("url", ""),
                    "price": price,
                    "price_type": price_type,
                    "city": city,
                    "address": address,
                    "province": prov_code,
                    "year": year,
                    "hours": hours,
                    "fuel_type": attrs.get("heavyequipfueltype"),
                    "condition": attrs.get("vehicletype"),
                    "equipment_type": attrs.get("heavyequiptype"),
                    "seller_type": attrs.get("forsaleby"),
                    "seller_source_id": str(poster_id) if poster_id is not None else None,
                    "image_url": image_url,
                    "search_keyword": keyword,
                    "search_province": province,
                    "activation_date": val.get("activationDate"),
                }
            )

        return items, total_count

    def normalize(self, raw: dict) -> dict | None:
        title = raw.get("title", "")
        if not title or not raw.get("listing_id"):
            return None

        price = raw.get("price")
        asking_price = float(price) if price else None

        # Build location string
        city = raw.get("city", "")
        prov = raw.get("province", "")
        location = f"{city}, {prov}".strip(", ") if city or prov else raw.get("address")

        # Extract make/model from title
        year = raw.get("year") or self.extract_year(title)
        make = None
        model = None
        if year:
            m = re.match(r"\d{4}\s+(\S+)\s+(.+)", title)
            if m:
                make = m.group(1)
                model = m.group(2).strip()

        desc = raw.get("description", "")
        specs = self.extract_specs(f"{title} {desc}")

        return {
            "external_id": raw["listing_id"],
            "url": raw.get("url", ""),
            "title": title,
            "category": raw.get("search_keyword"),
            "make": make,
            "model": model,
            "year": year,
            "condition": raw.get("condition"),
            "hours": raw.get("hours"),
            "location": location,
            "asking_price": asking_price,
            "currency": "CAD",
            "image_url": raw.get("image_url"),
            "description": desc,
            "specs": specs or None,
            "horsepower": specs.get("hp") if specs else None,
            "seller_source_id": raw.get("seller_source_id"),
            "seller_name": raw.get("seller_name"),
            "seller_account_type": raw.get("seller_account_type"),
            "seller_other_assets_url": raw.get("seller_other_assets_url"),
        }
