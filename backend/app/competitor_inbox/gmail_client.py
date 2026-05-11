"""Minimal async Gmail API client.

Authentication: OAuth2 refresh-token flow. We mint a short-lived access token
from the stored refresh token, then call the Gmail REST API directly with
aiohttp. No google-api-python-client dependency.

Surface:
    list_message_ids(after_epoch_seconds) -> list of message IDs (paged)
    fetch_message(message_id)              -> RawEmail

The list query restricts to messages newer than `after_epoch_seconds` so
each run only sees what's arrived since the last successful pull.
"""

from __future__ import annotations

import base64
import email
import email.utils
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from app.competitor_inbox.models import (
    GMAIL_OAUTH_CLIENT_ID,
    GMAIL_OAUTH_CLIENT_SECRET,
    GMAIL_OAUTH_REFRESH_TOKEN,
    GMAIL_USER_EMAIL,
    RawEmail,
)

_log = logging.getLogger(__name__)

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


# ---- OAuth ---------------------------------------------------------------


@dataclass
class _AccessToken:
    value: str
    expires_at: float  # epoch seconds


_cached_token: _AccessToken | None = None


async def _get_access_token(session: aiohttp.ClientSession) -> str:
    """Mint or reuse a Gmail API access token. ~1h validity, cached in memory."""
    import time

    global _cached_token
    if _cached_token and _cached_token.expires_at - 60 > time.time():
        return _cached_token.value

    payload = {
        "client_id": GMAIL_OAUTH_CLIENT_ID,
        "client_secret": GMAIL_OAUTH_CLIENT_SECRET,
        "refresh_token": GMAIL_OAUTH_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    async with session.post(OAUTH_TOKEN_URL, data=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()
    _cached_token = _AccessToken(
        value=data["access_token"],
        expires_at=time.time() + int(data.get("expires_in", 3600)),
    )
    return _cached_token.value


# ---- API calls -----------------------------------------------------------


async def list_message_ids(
    session: aiohttp.ClientSession,
    after_epoch_seconds: int | None = None,
    max_total: int = 500,
) -> list[str]:
    """Page through inbox messages, optionally restricted to after a timestamp."""
    token = await _get_access_token(session)
    headers = {"Authorization": f"Bearer {token}"}
    q = f"after:{after_epoch_seconds}" if after_epoch_seconds else ""
    ids: list[str] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"maxResults": 100}
        if q:
            params["q"] = q
        if page_token:
            params["pageToken"] = page_token
        async with session.get(
            f"{GMAIL_BASE}/messages", headers=headers, params=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
        for m in data.get("messages", []):
            ids.append(m["id"])
            if len(ids) >= max_total:
                return ids
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids


async def fetch_message(session: aiohttp.ClientSession, message_id: str) -> RawEmail:
    token = await _get_access_token(session)
    headers = {"Authorization": f"Bearer {token}"}
    params = {"format": "full"}
    async with session.get(
        f"{GMAIL_BASE}/messages/{message_id}", headers=headers, params=params
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return _parse_message(data)


# ---- Parsing -------------------------------------------------------------


def _parse_message(msg: dict[str, Any]) -> RawEmail:
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    from_header = headers.get("From", "")
    sender_name, sender_email = email.utils.parseaddr(from_header)
    sender_domain = sender_email.split("@", 1)[1].lower() if "@" in sender_email else ""

    received_at = _parse_date(headers.get("Date", ""))
    body_text, body_html = _extract_bodies(msg.get("payload", {}))

    return RawEmail(
        gmail_message_id=msg["id"],
        gmail_thread_id=msg.get("threadId", ""),
        sender_email=sender_email.lower(),
        sender_domain=sender_domain,
        sender_name=sender_name or None,
        subject=headers.get("Subject"),
        received_at=received_at,
        snippet=msg.get("snippet"),
        body_text=body_text,
        body_html=body_html,
        raw_headers=headers,
    )


def _parse_date(raw: str) -> datetime:
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _extract_bodies(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Walk the MIME tree to find text/plain + text/html parts."""
    text_body: str | None = None
    html_body: str | None = None

    def walk(part: dict[str, Any]) -> None:
        nonlocal text_body, html_body
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                decoded = ""
            if mime == "text/plain" and text_body is None:
                text_body = decoded
            elif mime == "text/html" and html_body is None:
                html_body = decoded
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return text_body, html_body


# ---- Sanity-check entry --------------------------------------------------


async def whoami() -> dict[str, Any]:
    """Quick test of credentials. Returns the authenticated user profile."""
    async with aiohttp.ClientSession() as session:
        token = await _get_access_token(session)
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(f"{GMAIL_BASE}/profile", headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()
