from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---- Env config -----------------------------------------------------------

GMAIL_OAUTH_CLIENT_ID = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "")
GMAIL_OAUTH_CLIENT_SECRET = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "")
GMAIL_OAUTH_REFRESH_TOKEN = os.environ.get("GMAIL_OAUTH_REFRESH_TOKEN", "")
GMAIL_USER_EMAIL = os.environ.get("GMAIL_USER_EMAIL", "")

# Pull at most this many messages per run. Gmail caps at 500 per page; we
# loop, but bound the total so a backlogged inbox doesn't blow a single run.
INBOX_FETCH_BUDGET = int(os.environ.get("COMPETITOR_INBOX_BUDGET", "200"))

# Extractor model — Haiku is plenty for classification + entity extraction.
EXTRACTOR_MODEL = os.environ.get(
    "COMPETITOR_INBOX_MODEL",
    "claude-haiku-4-5-20251001",
)


def have_credentials() -> bool:
    return all(
        (
            GMAIL_OAUTH_CLIENT_ID,
            GMAIL_OAUTH_CLIENT_SECRET,
            GMAIL_OAUTH_REFRESH_TOKEN,
            GMAIL_USER_EMAIL,
        )
    )


# ---- Domain types ---------------------------------------------------------

EXTRACTION_STATUSES = ("pending", "success", "failed", "skipped")
EVENT_TYPES = (
    "new_listing",
    "price_drop",
    "auction_reminder",
    "sold_notification",
    "featured",
    "newsletter",
    "other",
)
SENDER_CLASSES = (
    "marketplace",
    "broker",
    "auctioneer",
    "manufacturer",
    "newsletter",
    "industry_news",
    "unknown",
)


@dataclass
class RawEmail:
    """One inbound message — what we capture before any extraction."""

    gmail_message_id: str
    gmail_thread_id: str
    sender_email: str
    sender_domain: str
    sender_name: str | None
    subject: str | None
    received_at: datetime
    snippet: str | None
    body_text: str | None
    body_html: str | None
    raw_headers: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedSignal:
    """One structured signal pulled from an email. A single email can yield
    multiple signals (e.g. a digest with 5 new listings → 5 signals)."""

    event_type: str  # one of EVENT_TYPES
    listing_title: str | None = None
    listing_url: str | None = None
    listing_external_id: str | None = None
    listing_category_hint: str | None = None
    listing_location: str | None = None
    asking_price: float | None = None
    previous_price: float | None = None
    currency: str | None = None
    seller_hint: str | None = None
    urgency_signal: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    status: str  # one of EXTRACTION_STATUSES
    signals: list[ExtractedSignal] = field(default_factory=list)
    error: str | None = None
