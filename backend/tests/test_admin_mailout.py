"""Tests for GET /api/admin/mailout/sellers.csv — aggregated mailout export.

Scope: auth gating, CSV shape (header + row-per-seller), per-seller aggregations
(total_listings, active_listings_30d, total_ask_value), and filter params
(?source=, ?account_type=, ?min_active=).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

import pytest


def _seed_mailout_listings():
    """Inject a deterministic seller fixture into the in-memory test DB.

    Three distinct (source, seller_name) groups:
      • allsurplus / "Ritchie Energy Auctions"  — 3 listings, 2 active (last_seen ≤30d)
      • allsurplus / "Calgary Surplus Co"       — 1 listing, 1 active
      • bidspotter / "Big Iron Auctions"        — 2 listings, 0 active (all stale)
      • kijiji     / NULL seller_name           — excluded (NULL filter)
    """
    from tests import conftest
    now = datetime.now(timezone.utc)
    base = {
        "title": "Test Tank",
        "category": "tanks",
        "category_normalized": "tanks",
        "make": None, "model": None, "year": None,
        "horsepower": None, "hours": None, "weight_lbs": None,
        "condition": None, "location": None, "description": None,
        "fair_value": None, "is_active": True,
        "url": "https://example.com/listing",
    }
    conftest._db.listings.extend([
        # Ritchie — 3 listings, 2 active
        {**base, "id": "ml-1", "source": "allsurplus",
         "seller_name": "Ritchie Energy Auctions",
         "seller_account_type": "Auction House",
         "seller_other_assets_url": "https://ritchie.example/all",
         "event_contact_name": "Bob Smith",
         "event_contact_email": "bob@ritchie.example",
         "event_contact_phone": "555-1212",
         "asking_price": 50000, "current_bid": None,
         "first_seen": now - timedelta(days=120),
         "last_seen": now - timedelta(days=5),
         "category_normalized": "tanks",
         "url": "https://allsurplus.example/listing/r1"},
        {**base, "id": "ml-2", "source": "allsurplus",
         "seller_name": "Ritchie Energy Auctions",
         "seller_account_type": "Auction House",
         "asking_price": None, "current_bid": 30000,
         "first_seen": now - timedelta(days=80),
         "last_seen": now - timedelta(days=10),
         "category_normalized": "compressors",
         "url": "https://allsurplus.example/listing/r2"},
        {**base, "id": "ml-3", "source": "allsurplus",
         "seller_name": "Ritchie Energy Auctions",
         "seller_account_type": "Auction House",
         "asking_price": 25000, "current_bid": None,
         "first_seen": now - timedelta(days=200),
         "last_seen": now - timedelta(days=60),  # >30d → not active
         "category_normalized": "separators",
         "url": "https://allsurplus.example/listing/r3"},
        # Calgary Surplus — 1 listing, 1 active
        {**base, "id": "ml-4", "source": "allsurplus",
         "seller_name": "Calgary Surplus Co",
         "seller_account_type": "Dealer",
         "asking_price": 12000, "current_bid": None,
         "first_seen": now - timedelta(days=15),
         "last_seen": now - timedelta(days=2),
         "category_normalized": "pumps",
         "url": "https://allsurplus.example/listing/c1"},
        # Big Iron — 2 listings, 0 active (both stale)
        {**base, "id": "ml-5", "source": "bidspotter",
         "seller_name": "Big Iron Auctions",
         "seller_account_type": "Auction House",
         "asking_price": 8000, "current_bid": None,
         "first_seen": now - timedelta(days=400),
         "last_seen": now - timedelta(days=120),
         "category_normalized": "generators",
         "url": "https://bidspotter.example/listing/b1"},
        {**base, "id": "ml-6", "source": "bidspotter",
         "seller_name": "Big Iron Auctions",
         "seller_account_type": "Auction House",
         "asking_price": 5000, "current_bid": None,
         "first_seen": now - timedelta(days=300),
         "last_seen": now - timedelta(days=90),
         "category_normalized": "generators",
         "url": "https://bidspotter.example/listing/b2"},
        # NULL seller — excluded
        {**base, "id": "ml-7", "source": "kijiji",
         "seller_name": None,
         "seller_account_type": None,
         "asking_price": 1000, "current_bid": None,
         "first_seen": now - timedelta(days=5),
         "last_seen": now - timedelta(days=1),
         "category_normalized": "tanks",
         "url": "https://kijiji.example/listing/k1"},
    ])


# ── Auth gating ────────────────────────────────────────────────────────


def test_mailout_requires_token(client):
    resp = client.get("/api/admin/mailout/sellers.csv")
    assert resp.status_code == 401


def test_mailout_rejects_non_admin(client, user_headers):
    resp = client.get("/api/admin/mailout/sellers.csv", headers=user_headers)
    assert resp.status_code == 403


# ── CSV shape + content ────────────────────────────────────────────────


_EXPECTED_COLUMNS = [
    "source",
    "seller_name",
    "account_type",
    "total_listings",
    "active_listings_30d",
    "first_seen_on_fuelled",
    "last_seen_on_fuelled",
    "categories",
    "total_ask_value_usd",
    "contact_name",
    "contact_email",
    "contact_phone",
    "other_assets_url",
    "sample_listing_url",
]


def _parse_csv(body: str) -> tuple[list[str], list[dict]]:
    reader = csv.reader(io.StringIO(body))
    rows = list(reader)
    header = rows[0]
    data = [dict(zip(header, r)) for r in rows[1:]]
    return header, data


def test_mailout_returns_csv_with_expected_header(client, admin_headers):
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "mailout_sellers_" in resp.headers["content-disposition"]
    header, _ = _parse_csv(resp.text)
    assert header == _EXPECTED_COLUMNS


def test_mailout_dedupes_seller_to_single_row(client, admin_headers):
    """Ritchie has 3 listings → exactly 1 row in output."""
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    ritchie_rows = [r for r in rows if r["seller_name"] == "Ritchie Energy Auctions"]
    assert len(ritchie_rows) == 1
    r = ritchie_rows[0]
    assert r["source"] == "allsurplus"
    assert r["account_type"] == "Auction House"
    assert int(r["total_listings"]) == 3
    # 2 of 3 listings have last_seen within 30 days
    assert int(r["active_listings_30d"]) == 2


def test_mailout_excludes_null_seller_names(client, admin_headers):
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    # No NULL/empty seller_name rows should appear
    for r in rows:
        assert r["seller_name"] not in (None, "", "None")
    # Kijiji has only a NULL-seller listing → kijiji should NOT appear
    assert not any(r["source"] == "kijiji" for r in rows)


def test_mailout_aggregates_ask_value(client, admin_headers):
    """Ritchie: 50000 + 30000 (bid fallback) + 25000 = 105000."""
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    ritchie = next(r for r in rows if r["seller_name"] == "Ritchie Energy Auctions")
    assert int(ritchie["total_ask_value_usd"]) == 105000


def test_mailout_contact_info_picked_when_any_row_has_it(client, admin_headers):
    """Ritchie's listing ml-1 has contact info; the aggregated row should surface it."""
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    ritchie = next(r for r in rows if r["seller_name"] == "Ritchie Energy Auctions")
    assert ritchie["contact_name"] == "Bob Smith"
    assert ritchie["contact_email"] == "bob@ritchie.example"
    assert ritchie["contact_phone"] == "555-1212"
    assert ritchie["other_assets_url"] == "https://ritchie.example/all"


def test_mailout_default_sort_total_listings_desc(client, admin_headers):
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    totals = [int(r["total_listings"]) for r in rows]
    assert totals == sorted(totals, reverse=True)


# ── Filter params ──────────────────────────────────────────────────────


def test_mailout_filter_by_source(client, admin_headers):
    _seed_mailout_listings()
    # ?source=bidspotter — my fixture's only bidspotter seller is Big Iron;
    # confirm filtering is effective and no allsurplus/kijiji rows leak.
    resp = client.get("/api/admin/mailout/sellers.csv?source=bidspotter", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    assert all(r["source"] == "bidspotter" for r in rows)
    names = {r["seller_name"] for r in rows}
    assert "Big Iron Auctions" in names
    assert "Ritchie Energy Auctions" not in names  # different source


def test_mailout_filter_by_min_active(client, admin_headers):
    """min_active=2 → only sellers with ≥2 active listings in last 30d.

    Ritchie has 2, Calgary has 1, Big Iron has 0 → only Ritchie passes."""
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv?min_active=2", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    assert len(rows) == 1
    assert rows[0]["seller_name"] == "Ritchie Energy Auctions"


def test_mailout_filter_by_account_type(client, admin_headers):
    _seed_mailout_listings()
    resp = client.get("/api/admin/mailout/sellers.csv?account_type=Dealer", headers=admin_headers)
    _, rows = _parse_csv(resp.text)
    assert len(rows) == 1
    assert rows[0]["seller_name"] == "Calgary Surplus Co"
