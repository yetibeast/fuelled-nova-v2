"""End-to-end runner: pull new Gmail messages → store raw → extract signals.

Designed to be invoked from a scheduled job (Railway cron, GitHub Actions,
local cron, doesn't matter — pick one). Idempotent: re-running over the same
window is a no-op thanks to gmail_message_id uniqueness.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import aiohttp

from app.competitor_inbox import db, extractor, gmail_client
from app.competitor_inbox.models import INBOX_FETCH_BUDGET, have_credentials

_log = logging.getLogger(__name__)


@dataclass
class RunStats:
    fetched: int = 0
    inserted: int = 0
    duplicate: int = 0
    extracted: int = 0
    extract_failed: int = 0


async def run_once(extract_batch: int = 50) -> RunStats:
    """Fetch any new messages, then process up to `extract_batch` pending rows."""
    if not have_credentials():
        raise RuntimeError(
            "Gmail credentials missing. Set GMAIL_OAUTH_CLIENT_ID, "
            "GMAIL_OAUTH_CLIENT_SECRET, GMAIL_OAUTH_REFRESH_TOKEN, "
            "GMAIL_USER_EMAIL — see backend/app/competitor_inbox/README.md."
        )

    stats = RunStats()
    after = await db.latest_received_epoch()
    if after is not None:
        # Re-pull a 1-hour overlap to catch anything ingested out of order
        # (Gmail server-side timestamps vs. client-side after: filter).
        after = max(0, after - 3600)

    async with aiohttp.ClientSession() as session:
        ids = await gmail_client.list_message_ids(
            session,
            after_epoch_seconds=after,
            max_total=INBOX_FETCH_BUDGET,
        )
        _log.info("Gmail: %d candidate messages since %s", len(ids), after)

        for mid in ids:
            try:
                raw = await gmail_client.fetch_message(session, mid)
            except Exception:
                _log.exception("Failed to fetch message %s", mid)
                continue
            stats.fetched += 1
            row_id = await db.insert_raw_email(raw)
            if row_id is None:
                stats.duplicate += 1
            else:
                stats.inserted += 1

    # Extraction pass — runs over whatever's pending, not just freshly
    # inserted, so a previously-failed batch gets retried automatically.
    pending = await db.fetch_pending_emails(limit=extract_batch)
    _log.info("Extractor: processing %d pending rows", len(pending))
    for row in pending:
        try:
            result = await extractor.extract_signals(
                sender=row["sender_email"],
                subject=row["subject"],
                body=row["body_text"] or row["body_html"],
            )
        except Exception as e:
            _log.exception("Extractor crashed on email %s", row["id"])
            await db.write_signals_for_email(
                row["id"], [], status="failed", error=f"runner crash: {e}"
            )
            stats.extract_failed += 1
            continue
        await db.write_signals_for_email(
            row["id"],
            result.signals,
            status=result.status,
            error=result.error,
        )
        if result.status == "success":
            stats.extracted += 1
        else:
            stats.extract_failed += 1

    return stats


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    stats = asyncio.run(run_once())
    print(
        f"fetched={stats.fetched} inserted={stats.inserted} "
        f"duplicate={stats.duplicate} extracted={stats.extracted} "
        f"extract_failed={stats.extract_failed}"
    )


if __name__ == "__main__":
    main()
