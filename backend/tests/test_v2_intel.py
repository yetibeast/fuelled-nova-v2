"""Tests for /api/v2/intel/status and /api/v2/intel/queue.

Read-only admin endpoints. Verifies auth gating, response shape,
queue rollup, and recent-runs ordering.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta


def _seed_intel_listings():
    """Three seller groups (ACME x3, Beta x2, Gamma x1) so the queue has
    something to rank."""
    from tests import conftest
    now = datetime.now(timezone.utc)
    conftest._db.listings.extend([
        {"id": "vi-1", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://x/1", "last_seen": now, "first_seen": now, "is_active": True},
        {"id": "vi-2", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://x/2", "last_seen": now, "first_seen": now, "is_active": True},
        {"id": "vi-3", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://x/3", "last_seen": now, "first_seen": now, "is_active": True},
        {"id": "vi-4", "source": "kijiji", "seller_name": "Beta Dealers",
         "url": "https://y/1", "last_seen": now, "first_seen": now, "is_active": True},
        {"id": "vi-5", "source": "kijiji", "seller_name": "Beta Dealers",
         "url": "https://y/2", "last_seen": now, "first_seen": now, "is_active": True},
        {"id": "vi-6", "source": "allsurplus", "seller_name": "Gamma Liquidators",
         "url": "https://z/1", "last_seen": now, "first_seen": now, "is_active": True},
    ])


def _seed_run_history():
    """Two completed enrichment runs."""
    from tests import conftest
    now = datetime.now(timezone.utc)
    conftest._db.enrichment_runs.extend([
        {
            "run_id": "run-old",
            "started_at": now - timedelta(days=14),
            "finished_at": now - timedelta(days=14, minutes=-3),
            "trigger": "cron-weekly",
            "provider_chain": "claude_parallel",
            "sellers_total": 15,
            "sellers_succeeded": 12,
            "sellers_failed": 3,
            "contacts_added": 28,
            "cost_usd": 4.20,
            "notes": None,
        },
        {
            "run_id": "run-recent",
            "started_at": now - timedelta(days=7),
            "finished_at": now - timedelta(days=7, minutes=-5),
            "trigger": "cron-weekly",
            "provider_chain": "claude_parallel",
            "sellers_total": 20,
            "sellers_succeeded": 18,
            "sellers_failed": 2,
            "contacts_added": 42,
            "cost_usd": 6.20,
            "notes": None,
        },
    ])


def _seed_enriched_contacts():
    """Five contacts across two sellers — confirms totals math."""
    from tests import conftest
    now = datetime.now(timezone.utc)
    conftest._db.seller_contact_enrichment.extend([
        {"seller_name": "Existing 1", "source": "bidspotter",
         "contact_email": "a@x.com", "research_attempts": 1,
         "last_researched_at": now},
        {"seller_name": "Existing 1", "source": "bidspotter",
         "contact_email": "b@x.com", "research_attempts": 1,
         "last_researched_at": now},
        {"seller_name": "Existing 2", "source": "kijiji",
         "contact_email": "c@y.com", "research_attempts": 1,
         "last_researched_at": now},
        {"seller_name": "Existing 2", "source": "kijiji",
         "contact_email": "d@y.com", "research_attempts": 1,
         "last_researched_at": now},
        {"seller_name": "Existing 2", "source": "kijiji",
         "contact_email": "e@y.com", "research_attempts": 1,
         "last_researched_at": now},
    ])


# ── Auth gating ──────────────────────────────────────────────────────


def test_status_requires_auth(client):
    res = client.get("/api/v2/intel/status")
    assert res.status_code == 401


def test_queue_requires_auth(client):
    res = client.get("/api/v2/intel/queue")
    assert res.status_code == 401


def test_status_requires_admin_role(client, user_headers):
    res = client.get("/api/v2/intel/status", headers=user_headers)
    assert res.status_code == 403


def test_queue_requires_admin_role(client, user_headers):
    res = client.get("/api/v2/intel/queue", headers=user_headers)
    assert res.status_code == 403


# ── /status shape ────────────────────────────────────────────────────


def test_status_returns_expected_shape(client, admin_headers):
    _seed_intel_listings()
    _seed_run_history()
    _seed_enriched_contacts()

    res = client.get("/api/v2/intel/status", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()

    # Top-level keys per spec contract.
    assert set(body.keys()) >= {"queue", "recent_runs", "totals"}

    # Queue stats.
    queue = body["queue"]
    assert queue["total_pending"] >= 3   # at least our 3 seeded groups
    assert queue["never_researched"] == queue["total_pending"]  # nothing enriched yet for THESE sellers
    assert queue["stale"] == 0
    assert "top_10_by_listing_volume" in queue
    top = queue["top_10_by_listing_volume"]
    # ACME (3 listings) is the highest.
    assert top[0]["seller_name"] == "ACME Auctions"
    assert top[0]["listing_volume"] == 3
    assert top[0]["freshness"] == "never"

    # Recent runs ordered DESC by started_at.
    runs = body["recent_runs"]
    assert len(runs) == 2
    assert runs[0]["run_id"] == "run-recent"
    assert runs[1]["run_id"] == "run-old"
    assert runs[0]["sellers_succeeded"] == 18
    assert runs[0]["contacts_added"] == 42
    assert runs[0]["cost_usd"] == 6.20

    # Totals.
    totals = body["totals"]
    assert totals["sellers_enriched_all_time"] == 2   # Existing 1, Existing 2
    assert totals["contacts_in_db"] == 5
    assert totals["cost_to_date_usd"] == 10.4   # 4.20 + 6.20


def test_status_returns_zeros_on_empty_db(client, admin_headers):
    res = client.get("/api/v2/intel/status", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    # Pre-existing competitor seed has one seller (Bid-Only Test Seller)
    # so queue.total_pending isn't strictly zero — but recent_runs and
    # totals must be empty/zero.
    assert body["recent_runs"] == []
    assert body["totals"]["sellers_enriched_all_time"] == 0
    assert body["totals"]["contacts_in_db"] == 0
    assert body["totals"]["cost_to_date_usd"] == 0


# ── /queue paging ────────────────────────────────────────────────────


def test_queue_returns_pending_items(client, admin_headers):
    _seed_intel_listings()
    res = client.get("/api/v2/intel/queue", headers=admin_headers)
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    names = [item["seller_name"] for item in body["items"]]
    assert "ACME Auctions" in names
    assert "Beta Dealers" in names
    assert "Gamma Liquidators" in names
    assert body["limit"] == 100
    assert body["offset"] == 0


def test_queue_respects_limit_param(client, admin_headers):
    _seed_intel_listings()
    res = client.get("/api/v2/intel/queue?limit=1", headers=admin_headers)
    body = res.json()
    assert len(body["items"]) == 1
    # Highest-volume seller first.
    assert body["items"][0]["seller_name"] == "ACME Auctions"
    assert body["limit"] == 1


def test_queue_rejects_invalid_limit(client, admin_headers):
    res = client.get("/api/v2/intel/queue?limit=0", headers=admin_headers)
    assert res.status_code == 422
    res = client.get("/api/v2/intel/queue?limit=99999", headers=admin_headers)
    assert res.status_code == 422
