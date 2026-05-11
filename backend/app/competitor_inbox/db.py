"""DB helpers for the competitor inbox tables.

Idempotent INSERTs keyed on gmail_message_id — the same message arriving twice
(re-run, backfill) is a no-op.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from app.competitor_inbox.models import ExtractedSignal, RawEmail
from app.db.session import get_session

_log = logging.getLogger(__name__)


async def insert_raw_email(email: RawEmail) -> str | None:
    """Insert a raw email row. Returns the row id, or None if already present."""
    row_id = f"em_{uuid.uuid4().hex[:24]}"
    async with get_session() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO competitor_emails (
                    id, gmail_message_id, gmail_thread_id, sender_email,
                    sender_domain, sender_name, subject, received_at, snippet,
                    body_text, body_html, raw_headers, extraction_status
                ) VALUES (
                    :id, :gid, :tid, :sender_email, :sender_domain, :sender_name,
                    :subject, :received_at, :snippet, :body_text, :body_html,
                    CAST(:raw_headers AS JSONB), 'pending'
                )
                ON CONFLICT (gmail_message_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": row_id,
                "gid": email.gmail_message_id,
                "tid": email.gmail_thread_id,
                "sender_email": email.sender_email,
                "sender_domain": email.sender_domain,
                "sender_name": email.sender_name,
                "subject": email.subject,
                "received_at": email.received_at,
                "snippet": email.snippet,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "raw_headers": json.dumps(email.raw_headers),
            },
        )
        row = result.first()
        if row is None:
            await session.commit()
            return None
        await _upsert_sender(session, email)
        await session.commit()
        return row[0]


async def _upsert_sender(session, email: RawEmail) -> None:
    now = datetime.now(timezone.utc)
    await session.execute(
        text(
            """
            INSERT INTO competitor_email_senders
                (sender_email, sender_domain, display_name,
                 first_seen_at, last_seen_at, email_count)
            VALUES
                (:email, :domain, :name, :now, :now, 1)
            ON CONFLICT (sender_email) DO UPDATE SET
                last_seen_at = EXCLUDED.last_seen_at,
                email_count  = competitor_email_senders.email_count + 1,
                display_name = COALESCE(competitor_email_senders.display_name, EXCLUDED.display_name),
                updated_at   = EXCLUDED.last_seen_at
            """
        ),
        {
            "email": email.sender_email,
            "domain": email.sender_domain,
            "name": email.sender_name,
            "now": now,
        },
    )


async def fetch_pending_emails(limit: int = 50) -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            text(
                """
                SELECT id, sender_email, sender_domain, sender_name, subject,
                       received_at, snippet, body_text, body_html
                FROM competitor_emails
                WHERE extraction_status = 'pending'
                ORDER BY received_at ASC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def write_signals_for_email(
    email_id: str,
    signals: list[ExtractedSignal],
    status: str,
    error: str | None = None,
) -> None:
    async with get_session() as session:
        if signals:
            await session.execute(
                text("DELETE FROM competitor_email_signals WHERE email_id = :eid"),
                {"eid": email_id},
            )
            for sig in signals:
                await session.execute(
                    text(
                        """
                        INSERT INTO competitor_email_signals (
                            id, email_id, event_type, listing_title, listing_url,
                            listing_external_id, listing_category_hint,
                            listing_location, asking_price, previous_price,
                            currency, seller_hint, urgency_signal,
                            matched_listing_id, raw_extracted
                        ) VALUES (
                            :id, :eid, :event_type, :title, :url, :ext_id,
                            :cat, :loc, :price, :prev_price, :curr,
                            :seller, :urgency, :matched, CAST(:raw AS JSONB)
                        )
                        """
                    ),
                    {
                        "id": f"sig_{uuid.uuid4().hex[:24]}",
                        "eid": email_id,
                        "event_type": sig.event_type,
                        "title": sig.listing_title,
                        "url": sig.listing_url,
                        "ext_id": sig.listing_external_id,
                        "cat": sig.listing_category_hint,
                        "loc": sig.listing_location,
                        "price": sig.asking_price,
                        "prev_price": sig.previous_price,
                        "curr": sig.currency,
                        "seller": sig.seller_hint,
                        "urgency": sig.urgency_signal,
                        "matched": await _try_match_listing(session, sig.listing_url),
                        "raw": json.dumps(sig.raw),
                    },
                )
        await session.execute(
            text(
                """
                UPDATE competitor_emails
                SET extraction_status = :status,
                    extraction_error  = :error,
                    extracted_at      = NOW()
                WHERE id = :id
                """
            ),
            {"id": email_id, "status": status, "error": error},
        )
        await session.commit()


async def _try_match_listing(session, listing_url: str | None) -> str | None:
    """Best-effort match: if we've already scraped a listing at this URL,
    return its id so the signal links back to it. Used by Stale Targets
    enrichment later."""
    if not listing_url:
        return None
    result = await session.execute(
        text("SELECT id FROM listings WHERE url = :url LIMIT 1"),
        {"url": listing_url},
    )
    row = result.first()
    return row[0] if row else None


async def latest_received_epoch() -> int | None:
    """The receive timestamp of the newest message we've already ingested.
    Used to bound the Gmail list query so we don't re-fetch the world."""
    async with get_session() as session:
        result = await session.execute(
            text("SELECT MAX(received_at) FROM competitor_emails")
        )
        row = result.first()
        if not row or row[0] is None:
            return None
        return int(row[0].timestamp())
