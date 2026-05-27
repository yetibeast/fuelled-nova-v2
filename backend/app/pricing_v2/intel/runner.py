"""Recurring enrichment runner — picks sellers off enrichment_queue, calls
provider chain, upserts contacts, audits to enrichment_runs.

Designed as a pure async function so tests can inject a MockProvider and
a mock session factory. The CLI wrapper lives at backend/scripts/run_enrichment.py.

Per-seller flow:
  1. Pull up to 3 sample listing URLs from listings for hint context.
  2. Call provider.enrich_seller(seller_name, source, hints).
  3. If ProviderResult.error → bump research_attempts, set last_research_error.
  4. Else for each contact → INSERT … ON CONFLICT (seller_name, source,
     contact_email) DO UPDATE … then bump last_researched_at +
     research_attempts.
  5. Track cumulative cost. Abort the loop once cost_usd >= max_cost_usd.

The enrichment_runs row is inserted at start (status implicit via started_at +
finished_at) and updated with totals at the end.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from sqlalchemy import text

from app.pricing_v2.intel.providers.base import (
    Contact,
    EnrichmentProvider,
    ProviderResult,
)


@dataclass
class RunSummary:
    run_id: str
    sellers_total: int = 0
    sellers_succeeded: int = 0
    sellers_failed: int = 0
    contacts_added: int = 0
    cost_usd: float = 0.0
    aborted_for_cost: bool = False


_QUEUE_SQL = text(
    "SELECT seller_name, source, listing_volume, last_seen, "
    "       last_researched_at, attempts, freshness "
    "FROM enrichment_queue "
    "LIMIT :lim"
)

_SAMPLE_URLS_SQL = text(
    "SELECT url FROM listings "
    "WHERE seller_name = :seller AND source = :source "
    "  AND url IS NOT NULL "
    "ORDER BY last_seen DESC NULLS LAST "
    "LIMIT 3"
)

_INSERT_RUN_SQL = text(
    "INSERT INTO enrichment_runs (run_id, trigger, provider_chain) "
    "VALUES (:rid, :trig, :chain)"
)

_FINISH_RUN_SQL = text(
    "UPDATE enrichment_runs "
    "SET finished_at = NOW(), "
    "    sellers_total = :total, "
    "    sellers_succeeded = :ok, "
    "    sellers_failed = :fail, "
    "    contacts_added = :added, "
    "    cost_usd = :cost, "
    "    notes = :notes "
    "WHERE run_id = :rid"
)

# UPSERT one contact. Matches the existing unique index
# uq_seller_contact_enrichment_key on (seller_name, source, contact_email).
_UPSERT_CONTACT_SQL = text(
    "INSERT INTO seller_contact_enrichment ("
    "  seller_name, source, contact_name, contact_title, contact_email, "
    "  contact_phone, contact_linkedin, contact_confidence, "
    "  confidence_overall, location, outreach_notes, "
    "  enrichment_source, last_researched_at, research_attempts"
    ") VALUES ("
    "  :seller, :source, :name, :title, :email, "
    "  :phone, :linkedin, :confidence, "
    "  :confidence, :location, :notes, "
    "  :enrichment_source, NOW(), 1"
    ") "
    "ON CONFLICT (seller_name, source, contact_email) DO UPDATE SET "
    "  contact_name = EXCLUDED.contact_name, "
    "  contact_title = EXCLUDED.contact_title, "
    "  contact_phone = EXCLUDED.contact_phone, "
    "  contact_linkedin = EXCLUDED.contact_linkedin, "
    "  contact_confidence = EXCLUDED.contact_confidence, "
    "  confidence_overall = EXCLUDED.confidence_overall, "
    "  location = EXCLUDED.location, "
    "  outreach_notes = EXCLUDED.outreach_notes, "
    "  last_researched_at = NOW(), "
    "  research_attempts = seller_contact_enrichment.research_attempts + 1, "
    "  last_research_error = NULL"
)

# Record a failure when the provider returned no contacts (or errored).
# We still want to bump research_attempts and stash the error so /status
# can surface it. We INSERT a marker row with NULL email when no row exists
# for this (seller, source); ON CONFLICT it just increments + sets error.
_MARK_FAILURE_SQL = text(
    "INSERT INTO seller_contact_enrichment ("
    "  seller_name, source, contact_email, enrichment_source, "
    "  last_researched_at, research_attempts, last_research_error"
    ") VALUES ("
    "  :seller, :source, NULL, :enrichment_source, "
    "  NOW(), 1, :error"
    ") "
    "ON CONFLICT (seller_name, source, contact_email) DO UPDATE SET "
    "  last_researched_at = NOW(), "
    "  research_attempts = seller_contact_enrichment.research_attempts + 1, "
    "  last_research_error = :error"
)


async def _fetch_sample_urls(session: Any, seller: str, source: str) -> list[str]:
    res = await session.execute(_SAMPLE_URLS_SQL, {"seller": seller, "source": source})
    rows = res.fetchall()
    out: list[str] = []
    for r in rows:
        url = r[0] if not isinstance(r, dict) else r.get("url")
        if url:
            out.append(url)
    return out


def _row_get(row: Any, key: str, idx: int) -> Any:
    """Tolerant accessor for both dict-rows and tuple-rows."""
    if isinstance(row, dict):
        return row.get(key)
    try:
        return getattr(row, key)
    except AttributeError:
        try:
            return row[key]
        except (KeyError, TypeError, IndexError):
            try:
                return row[idx]
            except (IndexError, KeyError, TypeError):
                return None


async def run_enrichment(
    session_factory: Callable[[], Any],
    *,
    provider: EnrichmentProvider,
    limit: int = 20,
    max_cost_usd: float = 10.0,
    trigger: str = "manual",
    dry_run: bool = False,
    enrichment_source: str = "claude_parallel",
) -> RunSummary:
    """Execute one batch.

    session_factory: callable returning an async context manager that yields
    an AsyncSession (or our MockSession). Mirrors how get_session is used
    elsewhere in app.api.*.

    provider: an EnrichmentProvider instance.

    Returns a RunSummary with cumulative metrics.
    """
    run_id = str(uuid.uuid4())
    summary = RunSummary(run_id=run_id)

    # ── Phase 1: insert run row + pull queue + sample URLs ──
    async with session_factory() as session:
        if not dry_run:
            await session.execute(_INSERT_RUN_SQL, {
                "rid": run_id,
                "trig": trigger,
                "chain": provider.name,
            })
            await session.commit()

        res = await session.execute(_QUEUE_SQL, {"lim": limit})
        queue_rows = res.fetchall()
        summary.sellers_total = len(queue_rows)

        # Pre-fetch sample URLs while session is open.
        sellers: list[dict[str, Any]] = []
        for row in queue_rows:
            seller_name = _row_get(row, "seller_name", 0)
            source = _row_get(row, "source", 1)
            if not seller_name:
                continue
            urls = await _fetch_sample_urls(session, seller_name, source or "")
            sellers.append({
                "seller_name": seller_name,
                "source": source,
                "sample_urls": urls,
            })

    # ── Phase 2: provider calls (no DB session held during network) ──
    enrichment_results: list[tuple[dict[str, Any], ProviderResult]] = []
    for s in sellers:
        if summary.cost_usd >= max_cost_usd:
            summary.aborted_for_cost = True
            break
        try:
            result = await provider.enrich_seller(
                s["seller_name"],
                s["source"] or "",
                {"sample_listing_urls": s["sample_urls"]},
            )
        except Exception as exc:
            result = ProviderResult(
                contacts=[],
                cost_usd=0.0,
                raw_payload=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        summary.cost_usd += result.cost_usd
        enrichment_results.append((s, result))

    # ── Phase 3: upserts + run finalization ──
    if dry_run:
        for _, result in enrichment_results:
            if result.error or not result.contacts:
                summary.sellers_failed += 1
            else:
                summary.sellers_succeeded += 1
                summary.contacts_added += len(result.contacts)
        return summary

    async with session_factory() as session:
        for s, result in enrichment_results:
            if result.error:
                summary.sellers_failed += 1
                await session.execute(_MARK_FAILURE_SQL, {
                    "seller": s["seller_name"],
                    "source": s["source"],
                    "enrichment_source": enrichment_source,
                    "error": result.error[:500],
                })
                continue

            if not result.contacts:
                summary.sellers_failed += 1
                await session.execute(_MARK_FAILURE_SQL, {
                    "seller": s["seller_name"],
                    "source": s["source"],
                    "enrichment_source": enrichment_source,
                    "error": "no contacts returned",
                })
                continue

            summary.sellers_succeeded += 1
            for c in result.contacts:
                await session.execute(_UPSERT_CONTACT_SQL, {
                    "seller": s["seller_name"],
                    "source": s["source"],
                    "name": c.name,
                    "title": c.title,
                    "email": c.email,
                    "phone": c.phone,
                    "linkedin": c.linkedin,
                    "confidence": c.confidence,
                    "location": c.location,
                    "notes": c.outreach_notes,
                    "enrichment_source": enrichment_source,
                })
                summary.contacts_added += 1

        await session.execute(_FINISH_RUN_SQL, {
            "rid": run_id,
            "total": summary.sellers_total,
            "ok": summary.sellers_succeeded,
            "fail": summary.sellers_failed,
            "added": summary.contacts_added,
            "cost": round(summary.cost_usd, 3),
            "notes": "aborted on max_cost_usd" if summary.aborted_for_cost else None,
        })
        await session.commit()

    return summary
