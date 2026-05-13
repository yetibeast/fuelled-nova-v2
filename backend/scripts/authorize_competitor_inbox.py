#!/usr/bin/env python3
"""One-time OAuth dance to obtain a Gmail refresh token for the catch-all
competitor inbox.

Usage:
    1. Create a Google Cloud OAuth client (Desktop App type) in the project
       associated with the new dedicated Gmail account.
    2. Download the JSON credentials, or note the client_id + client_secret.
    3. Run this script with those credentials. It will print an authorization
       URL — open it in a browser signed into the COMPETITOR-INBOX Gmail
       account (NOT your personal Gmail). Approve the gmail.readonly scope.
    4. Paste the resulting authorization code back into this script.
    5. Save the printed refresh_token as GMAIL_OAUTH_REFRESH_TOKEN in your
       environment / Railway secrets.

Scopes requested: gmail.readonly (we only need to read).
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse

try:
    import aiohttp  # noqa: F401
except ImportError:
    print("aiohttp not installed. Run: pip install aiohttp", file=sys.stderr)
    sys.exit(1)

import asyncio

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # Manual copy-paste flow


async def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    import aiohttp

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, data=payload) as resp:
            resp.raise_for_status()
            return await resp.json()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()

    params = {
        "client_id": args.client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    print()
    print("Step 1 — open this URL in the COMPETITOR-INBOX Gmail account:")
    print()
    print(auth_url)
    print()
    print("Note: as of mid-2022 Google removed the manual-copy OOB flow for new")
    print("OAuth clients. If your client was created after that date, you'll see")
    print("an error_oob page. Workaround: edit the URL to use http://localhost")
    print("as redirect_uri, register http://localhost (any port) as an authorized")
    print("redirect URI in the OAuth client config, and copy the ?code= param")
    print("from the localhost URL after the redirect.")
    print()
    code = input("Step 2 — paste the authorization code here: ").strip()
    if not code:
        print("No code provided. Aborting.", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(exchange_code(args.client_id, args.client_secret, code))
    refresh_token = result.get("refresh_token")
    if not refresh_token:
        print("No refresh_token in response. Full response:", file=sys.stderr)
        print(result, file=sys.stderr)
        sys.exit(1)

    print()
    print("SUCCESS. Save these to your environment:")
    print()
    print(f"GMAIL_OAUTH_CLIENT_ID={args.client_id}")
    print(f"GMAIL_OAUTH_CLIENT_SECRET={args.client_secret}")
    print(f"GMAIL_OAUTH_REFRESH_TOKEN={refresh_token}")
    print("GMAIL_USER_EMAIL=<the address of the inbox you just authorized>")


if __name__ == "__main__":
    main()
