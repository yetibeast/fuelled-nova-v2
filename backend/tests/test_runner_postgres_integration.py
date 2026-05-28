"""Real-Postgres integration tests for the enrichment runner.

These tests use a fresh local Postgres database (`fuelled_test_intel`) rather
than the in-memory MockSession in conftest.py. The MockSession matches Python
dict semantics — which masks bugs that depend on Postgres-specific behavior
like NULL distinctness in unique indexes or transaction commit boundaries.

Setup contract (one-time, outside pytest — see SETUP at top of this file).

The fixture truncates the relevant tables between tests so each test starts
clean without re-creating the schema.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.pricing_v2.intel.providers.base import (
    Contact,
    ProviderResult,
)
from app.pricing_v2.intel.providers.mock import MockProvider
from app.pricing_v2.intel.runner import (
    _MARK_FAILURE_SQL,
    run_enrichment,
)


# Database URL: a local empty test DB with both migrations applied.
# Created via:
#   createdb fuelled_test_intel
#   psql -d fuelled_test_intel <<'SQL'
#   CREATE TABLE listings (id TEXT PRIMARY KEY, source TEXT, seller_name TEXT,
#                          url TEXT, first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ,
#                          is_active BOOLEAN, title TEXT);
#   SQL
#   psql -d fuelled_test_intel -f backend/scripts/migrations/2026-05-27_seller_contact_enrichment.sql
#   psql -d fuelled_test_intel -f backend/scripts/migrations/2026-05-27_enrichment_freshness.sql
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg:///fuelled_test_intel",
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def pg_engine():
    """Async engine for the test DB. Disposed after the test."""
    engine = create_async_engine(TEST_DB_URL, pool_size=2)
    yield engine
    _run(engine.dispose())


@pytest.fixture
def pg_session_factory(pg_engine):
    """An async session factory compatible with run_enrichment's contract.

    Each call enters a fresh AsyncSession; the runner manages commit/rollback.
    """
    _maker = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def factory():
        async with _maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    return factory


@pytest.fixture(autouse=True)
def _truncate_pg(pg_engine):
    """Clean slate before each test."""
    async def _truncate():
        async with pg_engine.begin() as conn:
            await conn.execute(text(
                "TRUNCATE seller_contact_enrichment, enrichment_runs, listings "
                "RESTART IDENTITY CASCADE"
            ))

    _run(_truncate())
    yield


async def _insert_listings(session_factory, sellers: list[tuple[str, str]]):
    """Helper: seed listings so enrichment_queue sees these sellers."""
    async with session_factory() as session:
        for i, (seller, source) in enumerate(sellers):
            await session.execute(text(
                "INSERT INTO listings (id, source, seller_name, url, first_seen, "
                "last_seen, is_active, title) "
                "VALUES (:id, :src, :seller, :url, NOW(), NOW(), TRUE, :title)"
            ), {
                "id": f"l-{i}-{uuid.uuid4().hex[:8]}",
                "src": source,
                "seller": seller,
                "url": f"https://example.com/{i}",
                "title": f"Listing {i}",
            })
        await session.commit()


async def _count_rows(pg_engine, sql: str, params=None) -> int:
    async with pg_engine.connect() as conn:
        res = await conn.execute(text(sql), params or {})
        return res.scalar() or 0


async def _fetch_one(pg_engine, sql: str, params=None):
    async with pg_engine.connect() as conn:
        res = await conn.execute(text(sql), params or {})
        return res.fetchone()


# ────────────────────────────────────────────────────────────────────────
# Bug C2 — NULL-conflict failure tracking
# ────────────────────────────────────────────────────────────────────────


def test_c2_repeated_failures_for_same_seller_collapse_to_one_row(
    pg_engine, pg_session_factory,
):
    """Three failures for the same (seller_name, source) must update
    a SINGLE row (research_attempts=3, last_research_error=most recent).

    Currently Postgres treats NULL as distinct in unique indexes, so
    INSERT … ON CONFLICT (seller_name, source, contact_email) does not
    trigger when contact_email is NULL — each failure creates a new row.
    """
    async def go():
        async with pg_session_factory() as session:
            for err in ("err1", "err2", "err3"):
                await session.execute(_MARK_FAILURE_SQL, {
                    "seller": "Test Seller",
                    "source": "bidspotter",
                    "enrichment_source": "mock",
                    "error": err,
                })
                await session.commit()

    _run(go())

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment "
        "WHERE seller_name = :s",
        {"s": "Test Seller"},
    ))
    assert n == 1, f"Expected 1 row, got {n} (NULL-conflict bug)"

    row = _run(_fetch_one(
        pg_engine,
        "SELECT research_attempts, last_research_error "
        "FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Test Seller"},
    ))
    assert row[0] == 3, f"Expected research_attempts=3, got {row[0]}"
    assert row[1] == "err3", f"Expected last_research_error='err3', got {row[1]!r}"


# ────────────────────────────────────────────────────────────────────────
# Bug I2 — Transaction boundaries / crash safety
# ────────────────────────────────────────────────────────────────────────


class CrashingProvider:
    """Succeeds on first N calls, raises on call N+1."""
    name = "mock"
    cost_per_query_usd = 0.0

    def __init__(self, succeed_n: int):
        self.succeed_n = succeed_n
        self.calls = 0

    async def enrich_seller(self, seller_name, source, hints):
        self.calls += 1
        if self.calls > self.succeed_n:
            raise RuntimeError("simulated crash")
        return ProviderResult(
            contacts=[Contact(
                name=f"Contact {self.calls}",
                email=f"c{self.calls}@example.com",
                confidence="medium",
            )],
            cost_usd=0.0,
        )


def test_i2_mid_batch_crash_preserves_completed_work(
    pg_engine, pg_session_factory,
):
    """If the runner crashes mid-batch, the DB must reflect:
      * contacts persisted for the sellers that finished BEFORE the crash
      * an enrichment_runs row with finished_at=NULL recording the partial run

    Currently the runner opens one session for the whole batch + finalization,
    so a crash rolls back ALL contacts even though provider calls (which cost
    real money) already happened.
    """
    # Patch the runner to RAISE during the seller loop. We do that by
    # constructing a CrashingProvider that succeeds twice then crashes
    # and wrapping run_enrichment so we capture the partial state.
    _run(_insert_listings(pg_session_factory, [
        ("Seller A", "bidspotter"),
        ("Seller B", "bidspotter"),
        ("Seller C", "bidspotter"),
        ("Seller D", "bidspotter"),
        ("Seller E", "bidspotter"),
    ]))

    # Wrap the runner: we want a "crash AFTER 2 successful per-seller
    # commits" simulation. Easiest path: provider succeeds for 2 sellers,
    # raises on the 3rd → result.error set on seller 3 → continue. That
    # doesn't crash the runner. We need a real crash. So we monkey-patch
    # session.execute to raise inside the upsert loop on the 3rd seller.
    #
    # Simplest realistic scenario: provider raises, runner catches and
    # would write a failure row — but a SECOND failure on the failure
    # write would crash. Instead we directly use a CrashingProvider that
    # makes the runner *itself* raise via injecting a bad value the
    # session can't serialize. To keep this test honest, we monkey-patch
    # the runner's upsert call to raise after 2 successful upserts.
    provider = MockProvider(contacts_per_seller=1, cost_usd=0.0)

    from app.pricing_v2.intel import runner as runner_mod
    original_execute_attr = "_orig_execute_for_crash_test"

    crash_state = {"upserts": 0}

    # Wrap pg_session_factory so the 3rd UPSERT raises.
    @asynccontextmanager
    async def crashing_factory():
        async with pg_session_factory() as session:
            real_execute = session.execute

            async def wrapped(sql, params=None):
                sql_text = getattr(sql, "text", str(sql))
                if "INSERT INTO seller_contact_enrichment" in sql_text \
                        and "ON CONFLICT" in sql_text \
                        and ":name" in sql_text:
                    crash_state["upserts"] += 1
                    if crash_state["upserts"] > 2:
                        raise RuntimeError("simulated DB crash mid-batch")
                return await real_execute(sql, params)

            session.execute = wrapped  # type: ignore[assignment]
            yield session

    with pytest.raises(RuntimeError, match="simulated DB crash"):
        _run(run_enrichment(
            crashing_factory,
            provider=provider,
            limit=10,
            trigger="manual",
        ))

    # After crash: contacts for the first 2 sellers must be persisted.
    persisted = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment "
        "WHERE confidence_overall IS NOT NULL",
    ))
    assert persisted == 2, (
        f"Expected 2 persisted contacts (sellers that finished before "
        f"crash), got {persisted}"
    )

    # And the enrichment_runs row must exist with finished_at=NULL.
    unfinished = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM enrichment_runs WHERE finished_at IS NULL",
    ))
    assert unfinished == 1, (
        f"Expected 1 unfinished enrichment_runs row, got {unfinished}"
    )


# ────────────────────────────────────────────────────────────────────────
# Bug I3 — Audit honesty: enrichment_runs.provider_chain reflects provider
# ────────────────────────────────────────────────────────────────────────
# Note: the audit column is `provider_chain` in the DDL but the spec brief
# says `enrichment_source`. The CURRENT runner code does NOT write to
# `enrichment_source` on enrichment_runs at all — there is no such column.
# What it DOES do is hardcode `enrichment_source` (the per-contact column)
# to "claude_parallel" via the runner's default kwarg, regardless of which
# provider was actually used.
#
# This test enforces: when provider=MockProvider, the contacts written to
# seller_contact_enrichment must have enrichment_source = 'mock', and the
# enrichment_runs.provider_chain must be 'mock'. Both must reflect the
# real provider, not a hardcoded string.


def test_i3_enrichment_source_reflects_actual_provider(
    pg_engine, pg_session_factory,
):
    _run(_insert_listings(pg_session_factory, [
        ("Honest Seller", "bidspotter"),
    ]))

    provider = MockProvider(contacts_per_seller=1, cost_usd=0.0)
    summary = _run(run_enrichment(
        pg_session_factory,
        provider=provider,
        limit=5,
        trigger="manual",
    ))
    assert summary.sellers_succeeded == 1

    contact_source = _run(_fetch_one(
        pg_engine,
        "SELECT enrichment_source FROM seller_contact_enrichment "
        "WHERE seller_name = 'Honest Seller'",
    ))
    assert contact_source[0] == "mock", (
        f"Expected enrichment_source='mock', got "
        f"{contact_source[0]!r} (hardcoded 'claude_parallel' bug)"
    )

    run_source = _run(_fetch_one(
        pg_engine,
        "SELECT provider_chain FROM enrichment_runs LIMIT 1",
    ))
    assert run_source[0] == "mock", (
        f"Expected provider_chain='mock', got {run_source[0]!r}"
    )


# ────────────────────────────────────────────────────────────────────────
# Bug I4 — Error logging completeness (MockSession is fine here)
# ────────────────────────────────────────────────────────────────────────


def test_i4_long_provider_exceptions_are_fully_logged(
    pg_engine, pg_session_factory, caplog,
):
    """Provider raises an exception with a long message (>500 chars).
    The DB column may stay truncated (size limit) but the Python log
    must capture the full message.
    """
    _run(_insert_listings(pg_session_factory, [
        ("Verbose Seller", "bidspotter"),
    ]))

    long_msg = "x" * 1000  # 1000 chars
    unique_marker = "MARKER_" + uuid.uuid4().hex

    class VerboseFailProvider:
        name = "mock"
        cost_per_query_usd = 0.0

        async def enrich_seller(self, seller_name, source, hints):
            raise RuntimeError(unique_marker + long_msg)

    with caplog.at_level(logging.ERROR, logger="app.pricing_v2.intel.runner"):
        _run(run_enrichment(
            pg_session_factory,
            provider=VerboseFailProvider(),
            limit=5,
            trigger="manual",
        ))

    # Full long message (or marker + most of it) appears in captured logs.
    combined_log = "\n".join(r.getMessage() for r in caplog.records)
    assert unique_marker in combined_log, (
        f"Unique marker not in logs (logger silent?). Captured:\n{combined_log[:500]}"
    )
    # And the full payload is preserved (>= 900 of the 1000 'x's logged).
    x_count = combined_log.count("x")
    assert x_count >= 900, (
        f"Long error truncated in log: only {x_count} 'x' chars captured "
        f"(expected ≥900)"
    )


# ────────────────────────────────────────────────────────────────────────
# Bug C2-followup — SUCCESS rows with contact_email = NULL must upsert
# cleanly. The failure-marker partial index now also covers any success
# row where Claude returned a contact without an email (real example:
# Andrea Sprute / Machinery Auctioneers — name + phone, no email). The
# runner's success INSERT uses ON CONFLICT (seller_name, source,
# contact_email), which does NOT match the partial index, so Postgres
# raises IntegrityError on the partial index instead of upserting.
# ────────────────────────────────────────────────────────────────────────


class NoEmailContactProvider:
    """Returns exactly one contact per call, with no email. Tracks calls."""

    name = "mock"
    cost_per_query_usd = 0.0

    def __init__(self, name: str = "Andrea Sprute",
                 title: str = "Auctioneer",
                 phone: str = "+1-210-648-2225",
                 location: str = "Texas"):
        self.name_val = name
        self.title_val = title
        self.phone_val = phone
        self.location_val = location
        self.calls = 0

    async def enrich_seller(self, seller_name, source, hints):
        self.calls += 1
        # Vary the title between calls so we can confirm "latest" wins.
        title = f"{self.title_val} v{self.calls}"
        return ProviderResult(
            contacts=[Contact(
                name=self.name_val,
                title=title,
                email=None,
                phone=self.phone_val,
                location=self.location_val,
                confidence="medium",
                outreach_notes="contact found via web research",
            )],
            cost_usd=0.0,
            raw_payload={"seller": seller_name},
        )


class MixedContactProvider:
    """Returns two contacts: one with email, one without."""

    name = "mock"
    cost_per_query_usd = 0.0

    async def enrich_seller(self, seller_name, source, hints):
        return ProviderResult(
            contacts=[
                Contact(
                    name="With Email",
                    title="Manager",
                    email="with.email@example.com",
                    phone="+1-555-0001",
                    location="Texas",
                    confidence="high",
                ),
                Contact(
                    name="No Email",
                    title="Auctioneer",
                    email=None,
                    phone="+1-555-0002",
                    location="Texas",
                    confidence="medium",
                ),
            ],
            cost_usd=0.0,
            raw_payload={"seller": seller_name},
        )


def test_c2fu_success_with_no_email_contact_upserts_cleanly(
    pg_engine, pg_session_factory,
):
    """Provider returns a single contact with contact_email=None for a
    new seller. Must persist as one row without IntegrityError.

    Current bug: success INSERT uses ON CONFLICT (seller_name, source,
    contact_email) — the partial index uq_seller_contact_enrichment_failure_marker
    blocks this with IntegrityError because (seller_name, source) already
    "exists" under that index (NULL email matches the partial predicate).
    """
    _run(_insert_listings(pg_session_factory, [
        ("Machinery Auctioneers", "bidspotter"),
    ]))

    provider = NoEmailContactProvider(name="Andrea Sprute")
    summary = _run(run_enrichment(
        pg_session_factory,
        provider=provider,
        limit=5,
        trigger="manual",
    ))
    assert summary.sellers_succeeded == 1, (
        f"Expected sellers_succeeded=1, got {summary.sellers_succeeded}"
    )

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment "
        "WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert n == 1, f"Expected 1 row, got {n}"

    row = _run(_fetch_one(
        pg_engine,
        "SELECT contact_name, contact_phone, research_attempts, "
        "       last_research_error "
        "FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert row[0] == "Andrea Sprute", f"contact_name was {row[0]!r}"
    assert row[1] == "+1-210-648-2225", f"contact_phone was {row[1]!r}"
    assert row[2] == 1, f"research_attempts was {row[2]}"
    assert row[3] is None, f"last_research_error was {row[3]!r} (expected NULL)"


async def _reset_research_freshness(pg_engine, seller: str):
    """Push last_researched_at back >90d so enrichment_queue re-surfaces
    the seller. The view excludes anything researched <90d ago, which
    blocks the idempotency tests from re-invoking the runner.
    """
    async with pg_engine.begin() as conn:
        await conn.execute(text(
            "UPDATE seller_contact_enrichment "
            "SET last_researched_at = NOW() - INTERVAL '120 days' "
            "WHERE seller_name = :s"
        ), {"s": seller})


def test_c2fu_repeated_no_email_research_increments_attempts(
    pg_engine, pg_session_factory,
):
    """Running the no-email success path twice for the same seller must
    update a single row in place and bump research_attempts to 2.
    """
    _run(_insert_listings(pg_session_factory, [
        ("Machinery Auctioneers", "bidspotter"),
    ]))

    provider = NoEmailContactProvider(name="Andrea Sprute")

    _run(run_enrichment(
        pg_session_factory, provider=provider, limit=5, trigger="manual",
    ))
    # Age the row so enrichment_queue re-surfaces this seller.
    _run(_reset_research_freshness(pg_engine, "Machinery Auctioneers"))
    _run(run_enrichment(
        pg_session_factory, provider=provider, limit=5, trigger="manual",
    ))

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment "
        "WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert n == 1, f"Expected 1 row after 2 runs, got {n}"

    row = _run(_fetch_one(
        pg_engine,
        "SELECT contact_name, contact_title, research_attempts "
        "FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert row[0] == "Andrea Sprute"
    # Title varies per call ('Auctioneer v1' then 'Auctioneer v2'); latest
    # call wins.
    assert row[1] == "Auctioneer v2", f"contact_title was {row[1]!r}"
    assert row[2] == 2, f"research_attempts was {row[2]}"


def test_c2fu_failure_marker_then_success_with_no_email_resolves(
    pg_engine, pg_session_factory,
):
    """First run records a failure marker (no contacts). Second run
    succeeds but the discovered contact has no email. The end state must
    be one row with the contact populated, attempts=2,
    last_research_error=NULL.

    Tests the failure→success transition through the partial index — the
    risky case where the failure row already occupies the partial-index
    slot when the success upsert runs.
    """
    _run(_insert_listings(pg_session_factory, [
        ("Machinery Auctioneers", "bidspotter"),
    ]))

    # Phase 1: provider returns empty → runner records a failure marker.
    empty_provider = MockProvider(contacts_per_seller=0, cost_usd=0.0)
    # MockProvider returns N contacts ONLY when seller_name doesn't start
    # with "empty-" or "fail-". contacts_per_seller=0 still returns 0
    # contacts (the list comprehension produces []).
    _run(run_enrichment(
        pg_session_factory, provider=empty_provider, limit=5, trigger="manual",
    ))

    failure_count = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert failure_count == 1, (
        f"Setup: expected 1 failure marker, got {failure_count}"
    )

    # Age the failure marker so the queue view re-surfaces this seller.
    _run(_reset_research_freshness(pg_engine, "Machinery Auctioneers"))

    # Phase 2: provider returns a no-email success contact.
    success_provider = NoEmailContactProvider(name="Andrea Sprute")
    _run(run_enrichment(
        pg_session_factory, provider=success_provider, limit=5, trigger="manual",
    ))

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert n == 1, f"Expected 1 row after failure→success, got {n}"

    row = _run(_fetch_one(
        pg_engine,
        "SELECT contact_name, contact_phone, research_attempts, "
        "       last_research_error "
        "FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Machinery Auctioneers"},
    ))
    assert row[0] == "Andrea Sprute", f"contact_name was {row[0]!r}"
    assert row[1] == "+1-210-648-2225", f"contact_phone was {row[1]!r}"
    assert row[2] == 2, f"research_attempts was {row[2]} (expected 2)"
    assert row[3] is None, (
        f"last_research_error was {row[3]!r} — success should clear it"
    )


def test_c2fu_success_with_email_still_works(
    pg_engine, pg_session_factory,
):
    """Regression guard: contact WITH an email still upserts cleanly via
    the original full-key conflict path. Re-running updates in place.
    """
    _run(_insert_listings(pg_session_factory, [
        ("Email Seller", "bidspotter"),
    ]))

    provider = MockProvider(contacts_per_seller=1, cost_usd=0.0)
    _run(run_enrichment(
        pg_session_factory, provider=provider, limit=5, trigger="manual",
    ))
    _run(_reset_research_freshness(pg_engine, "Email Seller"))
    _run(run_enrichment(
        pg_session_factory, provider=provider, limit=5, trigger="manual",
    ))

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Email Seller"},
    ))
    assert n == 1, f"Expected 1 row, got {n}"

    row = _run(_fetch_one(
        pg_engine,
        "SELECT contact_email, research_attempts "
        "FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Email Seller"},
    ))
    assert row[0] == "contact1@email-seller.com", f"email was {row[0]!r}"
    assert row[1] == 2, f"research_attempts was {row[1]}"


def test_c2fu_mixed_contacts_one_with_email_one_without(
    pg_engine, pg_session_factory,
):
    """Provider returns two contacts for the same seller: one has an
    email, one doesn't. Both must persist — the email contact via the
    full-key index, the no-email contact via the partial index. This is
    the realistic production case.
    """
    _run(_insert_listings(pg_session_factory, [
        ("Mixed Seller", "bidspotter"),
    ]))

    provider = MixedContactProvider()
    summary = _run(run_enrichment(
        pg_session_factory, provider=provider, limit=5, trigger="manual",
    ))
    assert summary.sellers_succeeded == 1
    assert summary.contacts_added == 2

    n = _run(_count_rows(
        pg_engine,
        "SELECT COUNT(*) FROM seller_contact_enrichment WHERE seller_name = :s",
        {"s": "Mixed Seller"},
    ))
    assert n == 2, f"Expected 2 rows (email + no-email), got {n}"

    with_email = _run(_fetch_one(
        pg_engine,
        "SELECT contact_name, contact_phone FROM seller_contact_enrichment "
        "WHERE seller_name = :s AND contact_email IS NOT NULL",
        {"s": "Mixed Seller"},
    ))
    assert with_email[0] == "With Email"
    assert with_email[1] == "+1-555-0001"

    without_email = _run(_fetch_one(
        pg_engine,
        "SELECT contact_name, contact_phone FROM seller_contact_enrichment "
        "WHERE seller_name = :s AND contact_email IS NULL",
        {"s": "Mixed Seller"},
    ))
    assert without_email[0] == "No Email"
    assert without_email[1] == "+1-555-0002"
