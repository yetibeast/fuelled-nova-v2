"""LLM-driven classification + extraction for competitor mailout emails.

We don't hand-code per-sender parsers. A small fast model (Haiku) reads the
subject + plaintext body and returns a JSON document with the event type and
zero-or-more structured listing signals. The full LLM output is preserved
in raw_extracted for debugging and re-processing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic

from app.competitor_inbox.models import (
    EVENT_TYPES,
    EXTRACTOR_MODEL,
    ExtractedSignal,
    ExtractionResult,
)
from app.config import ANTHROPIC_API_KEY

_log = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


_SYSTEM_PROMPT = """You are extracting structured signals from a competitor's marketplace email.

You'll be given the sender, subject, and plaintext body of one email. Return strict JSON describing what the email is and what listings (if any) it references.

Output schema:
{
  "primary_event_type": "<one of: new_listing, price_drop, auction_reminder, sold_notification, featured, newsletter, other>",
  "summary": "<one short sentence describing the email>",
  "signals": [
    {
      "event_type": "<one of the event types above>",
      "listing_title": "<short title or model description>",
      "listing_url": "<URL if present, else null>",
      "listing_external_id": "<vendor lot id / listing id if surfaced in URL or body, else null>",
      "listing_category_hint": "<rough category — e.g. compressor, separator, generator, pump, vehicle, lot — else null>",
      "listing_location": "<city, state/province, country — null if not stated>",
      "asking_price": <number or null>,
      "previous_price": <number or null — only for price drops, the OLD price>,
      "currency": "<USD, CAD, etc — null if not stated>",
      "seller_hint": "<seller / consignor / dealer name if stated, else null>",
      "urgency_signal": "<verbatim urgency phrase like 'Ends in 24 hours' or 'Final price reduction', else null>"
    }
  ]
}

Rules:
- "primary_event_type" is the dominant theme. A digest of 10 new listings = "new_listing". An auction-closing reminder = "auction_reminder". A generic newsletter with no specific lots = "newsletter".
- If the email contains 0 actionable listings (pure newsletter, signup confirmation, account update), return signals: [] but still set primary_event_type.
- Prices: extract the number only — strip $, commas, "USD". A "Was $50,000 Now $42,000" reads as asking_price=42000, previous_price=50000.
- URLs: only include URLs that point to a specific listing or lot page. Skip unsubscribe links, social media links, generic homepage URLs.
- Be conservative — null is better than guessing.
- Output ONLY the JSON object. No prose, no markdown fences."""


async def extract_signals(
    sender: str,
    subject: str | None,
    body: str | None,
) -> ExtractionResult:
    if not body and not subject:
        return ExtractionResult(status="skipped", error="empty email")

    # Truncate brutally — competitor digests can be huge. 12k chars of body is
    # plenty to find the headline + first few listings without burning tokens.
    truncated_body = (body or "")[:12000]
    user_msg = (
        f"From: {sender}\n"
        f"Subject: {subject or ''}\n\n"
        f"Body:\n{truncated_body}"
    )

    try:
        response = await _client.messages.create(
            model=EXTRACTOR_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        _log.exception("Anthropic call failed")
        return ExtractionResult(status="failed", error=str(e))

    raw_text = _extract_text(response)
    data = _parse_json(raw_text)
    if data is None:
        return ExtractionResult(
            status="failed",
            error=f"non-json response: {raw_text[:300]}",
        )

    primary = data.get("primary_event_type") or "other"
    if primary not in EVENT_TYPES:
        primary = "other"

    signals: list[ExtractedSignal] = []
    for s in data.get("signals", []) or []:
        evt = s.get("event_type") or primary
        if evt not in EVENT_TYPES:
            evt = "other"
        signals.append(
            ExtractedSignal(
                event_type=evt,
                listing_title=_clean(s.get("listing_title")),
                listing_url=_clean(s.get("listing_url")),
                listing_external_id=_clean(s.get("listing_external_id")),
                listing_category_hint=_clean(s.get("listing_category_hint")),
                listing_location=_clean(s.get("listing_location")),
                asking_price=_to_float(s.get("asking_price")),
                previous_price=_to_float(s.get("previous_price")),
                currency=_clean(s.get("currency")),
                seller_hint=_clean(s.get("seller_hint")),
                urgency_signal=_clean(s.get("urgency_signal")),
                raw=s,
            )
        )

    # If the LLM said "newsletter" with no signals, materialise one signal so
    # we still capture the fact that the email landed (useful for sender stats).
    if not signals:
        signals = [
            ExtractedSignal(
                event_type=primary,
                raw={"summary": data.get("summary") or ""},
            )
        ]

    return ExtractionResult(status="success", signals=signals)


# ---- helpers --------------------------------------------------------------


def _extract_text(response: Any) -> str:
    parts = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json(s: str) -> dict | None:
    if not s:
        return None
    # If the model wrapped the JSON in fences despite the instruction, unwrap.
    m = _JSON_FENCE.search(s)
    candidate = m.group(1) if m else s
    try:
        result = json.loads(candidate)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


def _clean(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
