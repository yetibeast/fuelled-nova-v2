from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

AUCTION_SOURCES = {
    "ritchiebros",
    "ironplanet",
    "govdeals",
    "bidspotter",
    "allsurplus",
    "energyauctions",
}

_CATEGORY_THRESHOLDS = [
    (180, ("compressor", "engine", "generator", "vru", "pump jack")),
    (270, ("separator", "treater", "dehydrator", "line heater", "scrubber")),
]


def row_value(row: Any, key: str, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if hasattr(row, "_mapping"):
        return row._mapping.get(key, default)
    return getattr(row, key, default)


def row_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if hasattr(row, "_data"):
        return dict(row._data)
    return {key: getattr(row, key) for key in dir(row) if not key.startswith("_")}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def normalized_category(row: Any) -> str:
    return normalize_text(row_value(row, "category_normalized") or row_value(row, "category"))


def stale_threshold_days(category: str) -> int:
    normalized = normalize_text(category)
    for days, keywords in _CATEGORY_THRESHOLDS:
        if any(keyword in normalized for keyword in keywords):
            return days
    return 365


def is_auction_source(source: str | None) -> bool:
    return normalize_text(source) in AUCTION_SOURCES


def is_recently_seen(last_seen: datetime | None, now: datetime) -> bool:
    return bool(last_seen and last_seen >= now - timedelta(days=30))


def data_quality_score(row: Any) -> int:
    checks = [
        bool(row_value(row, "make")),
        bool(row_value(row, "model")),
        row_value(row, "year") is not None,
        bool(row_value(row, "condition")),
        row_value(row, "hours") is not None,
        bool(row_value(row, "location")),
    ]
    return round(sum(1 for ok in checks if ok) / len(checks) * 15)


def _peer_prices(listing: Any, peers: list[dict[str, Any]]) -> list[float]:
    category = normalized_category(listing)
    listing_id = row_value(listing, "id")
    prices = []
    same_year_prices = []
    listing_year = row_value(listing, "year")

    for peer in peers:
        if row_value(peer, "id") == listing_id:
            continue
        if normalized_category(peer) != category:
            continue
        price = row_value(peer, "asking_price")
        if price is None or price <= 0:
            continue
        prices.append(float(price))
        peer_year = row_value(peer, "year")
        if listing_year is not None and peer_year is not None and abs(peer_year - listing_year) <= 2:
            same_year_prices.append(float(price))

    if len(same_year_prices) >= 3:
        return same_year_prices
    return prices


def build_stale_candidate(listing: Any, peers: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any] | None:
    now = now or datetime.now(timezone.utc)
    source = normalize_text(row_value(listing, "source"))
    if source == "fuelled":
        return None

    asking_price = row_value(listing, "asking_price")
    if asking_price is None or asking_price <= 0:
        return None

    first_seen = row_value(listing, "first_seen")
    last_seen = row_value(listing, "last_seen")
    if not first_seen or not is_recently_seen(last_seen, now):
        return None

    days_listed = (now - first_seen).days
    threshold = stale_threshold_days(normalized_category(listing))
    if days_listed < threshold:
        return None

    peer_prices = _peer_prices(listing, peers)
    peer_count = len(peer_prices)
    peer_median = round(median(peer_prices), 2) if peer_prices else None

    overdue_ratio = max(days_listed - threshold, 0) / max(threshold, 1)
    age_score = min(35, round(12 + overdue_ratio * 35))

    negotiability_score = 0
    if peer_median and asking_price > peer_median:
        negotiability_score = min(20, round(((asking_price - peer_median) / peer_median) * 30))

    liquidity_score = min(20, peer_count * 4)
    quality_score = data_quality_score(listing)
    source_score = 0 if is_auction_source(source) else 10

    acquisition_score = min(
        100,
        age_score + negotiability_score + liquidity_score + quality_score + source_score,
    )
    promotable = (not is_auction_source(source)) and peer_count >= 3

    reason_parts = [
        f"{days_listed} days listed",
        f"{peer_count} priced peers" if peer_count else "limited peer coverage",
    ]
    if peer_median:
        reason_parts.append(f"ask vs peer median {int(asking_price - peer_median):,}")

    return {
        "source_listing_id": row_value(listing, "id"),
        "title": row_value(listing, "title"),
        "source": row_value(listing, "source"),
        "category": row_value(listing, "category_normalized") or row_value(listing, "category"),
        "asking_price": float(asking_price),
        "location": row_value(listing, "location"),
        "url": row_value(listing, "url"),
        "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else first_seen,
        "last_seen": last_seen.isoformat() if hasattr(last_seen, "isoformat") else last_seen,
        "days_listed": days_listed,
        "stale_threshold_days": threshold,
        "peer_median": peer_median,
        "peer_count": peer_count,
        "acquisition_score": acquisition_score,
        "promotable": promotable,
        "reason": ", ".join(reason_parts),
        "make": row_value(listing, "make"),
        "model": row_value(listing, "model"),
        "year": row_value(listing, "year"),
        "condition": row_value(listing, "condition"),
        "hours": row_value(listing, "hours"),
        "horsepower": row_value(listing, "horsepower"),
    }


def build_draft_payload(target: Any) -> dict[str, Any]:
    return {
        "title": row_value(target, "title"),
        "category": row_value(target, "category"),
        "make": row_value(target, "make"),
        "model": row_value(target, "model"),
        "year": row_value(target, "year"),
        "condition": row_value(target, "condition") or "Used",
        "location": row_value(target, "location"),
        "competitor_source": row_value(target, "source"),
        "competitor_url": row_value(target, "url"),
        "competitor_asking_price": row_value(target, "asking_price"),
        "peer_median": row_value(target, "peer_median"),
        "peer_count": row_value(target, "peer_count"),
        "listing_notes": "Auto-generated from stale competitor inventory. Pricing review still required.",
    }


def target_record_from_candidate(candidate: dict[str, Any], note: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"acq_{candidate['source_listing_id']}",
        "source_listing_id": candidate["source_listing_id"],
        "source": candidate["source"],
        "title": candidate["title"],
        "category": candidate["category"],
        "asking_price": candidate["asking_price"],
        "location": candidate["location"],
        "url": candidate["url"],
        "first_seen": candidate["first_seen"],
        "last_seen": candidate["last_seen"],
        "days_listed": candidate["days_listed"],
        "stale_threshold_days": candidate["stale_threshold_days"],
        "peer_median": candidate["peer_median"],
        "peer_count": candidate["peer_count"],
        "acquisition_score": candidate["acquisition_score"],
        "promotable": candidate["promotable"],
        "status": "new",
        "assigned_to": None,
        "notes": note,
        "draft_payload": None,
        "created_at": now,
        "updated_at": now,
        "make": candidate.get("make"),
        "model": candidate.get("model"),
        "year": candidate.get("year"),
        "condition": candidate.get("condition"),
        "hours": candidate.get("hours"),
        "horsepower": candidate.get("horsepower"),
    }


def dump_json(value: Any) -> str:
    return json.dumps(value)
