"""Tests for the recurring enrichment runner.

The runner is a pure async function (app.pricing_v2.intel.runner.run_enrichment)
that takes an injectable session_factory + provider. Tests use MockProvider
and the in-memory MockSession from conftest.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

import pytest

from app.pricing_v2.intel.providers.mock import MockProvider
from app.pricing_v2.intel.runner import run_enrichment


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _seed_intel_listings():
    """Add a handful of distinct (seller_name, source) groups to the
    in-memory listings table so enrichment_queue has something to chew on."""
    from tests import conftest
    now = datetime.now(timezone.utc)
    extra = [
        # Two sellers with multiple listings → high listing_volume.
        {"id": "il-1", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://bidspotter.com/lot/1", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Compressor 1"},
        {"id": "il-2", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://bidspotter.com/lot/2", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Compressor 2"},
        {"id": "il-3", "source": "bidspotter", "seller_name": "ACME Auctions",
         "url": "https://bidspotter.com/lot/3", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Compressor 3"},
        {"id": "il-4", "source": "kijiji", "seller_name": "Beta Dealers",
         "url": "https://kijiji.com/lot/1", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Generator"},
        {"id": "il-5", "source": "kijiji", "seller_name": "Beta Dealers",
         "url": "https://kijiji.com/lot/2", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Generator 2"},
        # Singleton seller.
        {"id": "il-6", "source": "allsurplus", "seller_name": "Gamma Liquidators",
         "url": "https://allsurplus.com/lot/9", "last_seen": now, "first_seen": now,
         "is_active": True, "title": "Tank"},
    ]
    conftest._db.listings.extend(extra)
    return extra


@asynccontextmanager
async def _mock_factory():
    from tests import conftest
    yield conftest.MockSession(conftest._db)


# ── Queue view ─────────────────────────────────────────────────────────


def test_enrichment_queue_returns_unresearched_sellers_ranked_by_volume():
    from tests import conftest
    _seed_intel_listings()
    res = _run(_query_queue(conftest))
    rows = res.fetchall()
    names = [r._data["seller_name"] for r in rows]
    # ACME (3 listings) ranks first; Beta (2) ranks above singletons.
    assert names[0] == "ACME Auctions"
    assert names[1] == "Beta Dealers"
    # All other seeded sellers (Gamma + the pre-existing Bid-Only Test
    # Seller in the conftest competitor seed) show up but order between
    # singletons isn't meaningful.
    assert "Gamma Liquidators" in names
    # All marked 'never' since seller_contact_enrichment is empty.
    assert all(r._data["freshness"] == "never" for r in rows)


async def _query_queue(conftest_mod):
    from sqlalchemy import text
    async with _mock_factory() as session:
        return await session.execute(
            text("SELECT * FROM enrichment_queue LIMIT :lim"),
            {"lim": 10},
        )


def test_enrichment_queue_excludes_fresh_sellers():
    """Sellers researched within the last 90 days should NOT appear."""
    from tests import conftest
    _seed_intel_listings()
    now = datetime.now(timezone.utc)
    # Mark ACME as fresh (researched today).
    conftest._db.seller_contact_enrichment.append({
        "seller_name": "ACME Auctions",
        "source": "bidspotter",
        "contact_email": "x@acme.com",
        "last_researched_at": now,
        "research_attempts": 1,
    })
    res = _run(_query_queue(conftest))
    rows = res.fetchall()
    names = [r._data["seller_name"] for r in rows]
    assert "ACME Auctions" not in names
    assert "Beta Dealers" in names


def test_enrichment_queue_excludes_sellers_with_3_or_more_attempts():
    from tests import conftest
    _seed_intel_listings()
    conftest._db.seller_contact_enrichment.append({
        "seller_name": "ACME Auctions",
        "source": "bidspotter",
        "contact_email": None,
        "last_researched_at": None,
        "research_attempts": 3,
    })
    res = _run(_query_queue(conftest))
    rows = res.fetchall()
    names = [r._data["seller_name"] for r in rows]
    assert "ACME Auctions" not in names


# ── Runner happy path ──────────────────────────────────────────────────


def test_runner_inserts_contacts_and_records_run():
    from tests import conftest
    _seed_intel_listings()
    provider = MockProvider(contacts_per_seller=2, cost_usd=0.05)

    summary = _run(run_enrichment(
        _mock_factory,
        provider=provider,
        limit=10,
        max_cost_usd=10.0,
        trigger="manual",
    ))

    # We seeded 3 distinct sellers + the pre-existing "Bid-Only Test
    # Seller" already in the conftest competitor fixture = 4 total.
    assert summary.sellers_total == 4
    assert summary.sellers_succeeded == 4
    assert summary.sellers_failed == 0
    assert summary.contacts_added == 8   # 4 sellers × 2 contacts each
    assert summary.cost_usd == pytest.approx(0.20, rel=1e-3)

    # Contacts persisted to seller_contact_enrichment.
    rows = conftest._db.seller_contact_enrichment
    assert len(rows) == 8
    assert all(r["last_researched_at"] is not None for r in rows)
    assert all(r["research_attempts"] == 1 for r in rows)

    # Run row finalized.
    assert len(conftest._db.enrichment_runs) == 1
    run = conftest._db.enrichment_runs[0]
    assert run["finished_at"] is not None
    assert run["sellers_succeeded"] == 4
    assert run["contacts_added"] == 8
    assert run["trigger"] == "manual"
    assert run["provider_chain"] == "mock"


def test_runner_respects_limit_param():
    from tests import conftest
    _seed_intel_listings()
    provider = MockProvider()

    summary = _run(run_enrichment(
        _mock_factory,
        provider=provider,
        limit=2,
        trigger="manual",
    ))

    assert summary.sellers_total == 2
    assert len(provider.calls) == 2


def test_runner_aborts_on_max_cost():
    from tests import conftest
    _seed_intel_listings()
    # Each call costs $5; budget $7 → only one full call fits before abort.
    provider = MockProvider(contacts_per_seller=1, cost_usd=5.0)

    summary = _run(run_enrichment(
        _mock_factory,
        provider=provider,
        limit=10,
        max_cost_usd=7.0,
        trigger="manual",
    ))

    # First call costs $5 (under budget); after that cost_usd=$5 < $7 so a
    # second call is allowed — bringing total to $10 which trips the abort
    # before any further calls. Result: exactly 2 provider calls.
    assert len(provider.calls) == 2
    assert summary.aborted_for_cost is True
    assert summary.cost_usd == pytest.approx(10.0)


def test_runner_records_failure_without_aborting():
    """One provider failure must NOT abort the loop. The seller gets a
    failure-marker row with research_attempts incremented + error stored."""
    from tests import conftest
    # Two sellers, one will fail.
    _seed_intel_listings()
    # Rename ACME to 'fail-ACME Auctions' by editing the seeded listings.
    for l in conftest._db.listings:
        if l.get("seller_name") == "ACME Auctions":
            l["seller_name"] = "fail-ACME Auctions"

    provider = MockProvider()
    summary = _run(run_enrichment(
        _mock_factory,
        provider=provider,
        limit=10,
        trigger="manual",
    ))

    assert summary.sellers_failed >= 1
    assert summary.sellers_succeeded >= 1
    # Failure marker row exists for the failed seller.
    failure_rows = [
        r for r in conftest._db.seller_contact_enrichment
        if r["seller_name"] == "fail-ACME Auctions"
    ]
    assert len(failure_rows) == 1
    assert failure_rows[0]["research_attempts"] == 1
    assert failure_rows[0]["last_research_error"] is not None
    # Run row has the failure counted.
    run = conftest._db.enrichment_runs[0]
    assert run["sellers_failed"] >= 1


def test_runner_upsert_is_idempotent_on_repeat_run():
    """Running twice with the same provider+queue must NOT create duplicate
    contacts (UNIQUE on seller_name, source, contact_email)."""
    from tests import conftest
    _seed_intel_listings()
    provider = MockProvider(contacts_per_seller=1)

    summary1 = _run(run_enrichment(_mock_factory, provider=provider, trigger="manual"))

    # After the first run all sellers are "fresh" (just researched). Queue
    # will exclude them. Force re-research by rewinding last_researched_at.
    past = datetime.now(timezone.utc) - timedelta(days=120)
    for r in conftest._db.seller_contact_enrichment:
        r["last_researched_at"] = past
        r["research_attempts"] = 1

    summary2 = _run(run_enrichment(_mock_factory, provider=provider, trigger="manual"))

    # Total contacts unchanged: same emails get UPDATEd, not inserted.
    contact_rows = conftest._db.seller_contact_enrichment
    assert len(contact_rows) == summary1.contacts_added
    # research_attempts bumped on each re-research.
    assert all(r["research_attempts"] == 2 for r in contact_rows)


def test_runner_dry_run_skips_writes():
    from tests import conftest
    _seed_intel_listings()
    provider = MockProvider()

    summary = _run(run_enrichment(
        _mock_factory,
        provider=provider,
        limit=10,
        trigger="manual",
        dry_run=True,
    ))

    # Provider was called for all 4 sellers (3 seeded + 1 pre-existing).
    assert len(provider.calls) == 4
    # But nothing persisted.
    assert conftest._db.seller_contact_enrichment == []
    assert conftest._db.enrichment_runs == []
    # Summary still tracks what *would* have happened.
    assert summary.sellers_succeeded == 4
    assert summary.contacts_added == 4


def test_runner_marks_empty_contacts_as_failure():
    """Provider returns 0 contacts but no error — runner still bumps attempts
    + records 'no contacts returned' so we don't keep hammering."""
    from tests import conftest
    _seed_intel_listings()
    for l in conftest._db.listings:
        if l.get("seller_name") == "Gamma Liquidators":
            l["seller_name"] = "empty-Gamma"

    provider = MockProvider()
    summary = _run(run_enrichment(_mock_factory, provider=provider, trigger="manual"))

    empty_rows = [
        r for r in conftest._db.seller_contact_enrichment
        if r["seller_name"] == "empty-Gamma"
    ]
    assert len(empty_rows) == 1
    assert empty_rows[0]["last_research_error"] == "no contacts returned"
    assert summary.sellers_failed >= 1
