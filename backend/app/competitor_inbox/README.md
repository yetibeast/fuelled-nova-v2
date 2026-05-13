# Competitor Inbox

Catch-all pipeline for competitor mailout emails. Subscribes one dedicated Gmail account to every competitor's mailing list, pulls inbound messages, and runs an LLM extractor that classifies each email and pulls out structured signals (new listings, price drops, sold notifications, auction reminders, featured lots, urgency markers).

Sender-agnostic by design — no per-marketplace parsers. Covers both online marketplaces we already scrape AND mail-only brokers/auctioneers that don't have a website to scrape.

---

## What this delivers

For Mark's 2026-04-07 "Next agentic tool" spec: the catch-all-email piece Curtis promised in his 4/7 reply ("I'm going to get an Obsidian email to capture these"). Backend-only this pass — surface in Nova later if it proves out.

## Tables (see `backend/scripts/migrations/2026-05-10_competitor_email_capture.sql`)

- `competitor_emails` — one row per inbound message, raw capture
- `competitor_email_signals` — one row per extracted listing/event
- `competitor_email_senders` — sender registry (who's writing, how often)

## Manual setup — what Curtis needs to do once

### 1. Create the dedicated Gmail account
Use a fresh Gmail (or Google Workspace alias) — something like `fuelled-competitor-feeds@gmail.com`. This is the address you'll hand to competitor signup forms.

### 2. Create a Google Cloud OAuth client
Sign in to the new account, go to https://console.cloud.google.com → create a new project → APIs & Services → Credentials → Create credentials → OAuth client ID → Application type "Desktop app". Save the client_id and client_secret.

Enable the Gmail API on the same project (APIs & Services → Library → "Gmail API" → Enable).

### 3. Obtain a refresh token
```bash
PYTHONPATH=backend python3 backend/scripts/authorize_competitor_inbox.py \
    --client-id <YOUR_CLIENT_ID> \
    --client-secret <YOUR_CLIENT_SECRET>
```
Follow the printed instructions. The script will print the refresh_token to save.

### 4. Set environment variables
```
GMAIL_OAUTH_CLIENT_ID=...
GMAIL_OAUTH_CLIENT_SECRET=...
GMAIL_OAUTH_REFRESH_TOKEN=...
GMAIL_USER_EMAIL=fuelled-competitor-feeds@gmail.com
COMPETITOR_INBOX_BUDGET=200            # max msgs per run (default 200)
COMPETITOR_INBOX_MODEL=claude-haiku-4-5-20251001
```
Local: add to `backend/.env`. Production: add to Railway secrets on the backend service.

### 5. Apply the migration
```bash
/opt/homebrew/opt/postgresql@16/bin/psql "$DATABASE_URL" \
    -f backend/scripts/migrations/2026-05-10_competitor_email_capture.sql
```

### 6. Subscribe the new inbox to competitor mailing lists
Manual one-time. Suggested list (mix of scraped + mail-only):

**Marketplaces we already scrape (mailing list still useful for first-look + price-drop alerts):**
- Ritchie Bros (rbauction.com) — "Watch this lot" alerts + sale announcements
- IronPlanet — daily new-lot digests
- AllSurplus / Liquidity Services — event mailers
- BidSpotter — auction reminders
- GovDeals — closing-today alerts
- EquipmentTrader — saved-search alerts
- Machinio — saved-search alerts
- Surplus Record — weekly digest

**Mail-only / no-marketplace:**
- Salvex newsletter
- Sage Auctions / regional auctioneers
- Local equipment brokers (Cole Rivet / Everleigh Industrial type contacts)
- Industry-specific mailers (oilfield brokers, refinery surplus, etc.)

Add more over time. The pipeline doesn't care — every new sender lands as a row in `competitor_email_senders` so you'll see "who's writing to us" without configuring anything.

## Running the pipeline

### One-off (local / smoke test)
```bash
PYTHONPATH=backend python3 -m app.competitor_inbox.runner
```
Prints `fetched=X inserted=Y duplicate=Z extracted=N extract_failed=M`. Idempotent — safe to re-run.

### Test the extractor without Gmail access
```bash
PYTHONPATH=backend python3 backend/scripts/test_competitor_extractor.py
```
Runs the three bundled fixture emails through the extractor. Needs ANTHROPIC_API_KEY but not Gmail credentials or DB.

### Production schedule
Pick one of:
- **Railway cron service** — `railway add cron`, command `python3 -m app.competitor_inbox.runner`, every 30 min.
- **GitHub Actions scheduled workflow** with `DATABASE_URL` + Gmail secrets exported.
- **Existing backend lifespan task** — register `run_once()` on a `BackgroundTasks` loop in `main.py`.

The runner is idempotent and self-bounded (`COMPETITOR_INBOX_BUDGET`), so any cadence is fine. 30-60 min is plenty — competitor mailouts aren't time-critical.

## Costs

Per email: 1 Haiku call, ~12k input tokens worst-case, ~500 output tokens. At Haiku pricing that's about $0.012 per email. At 200 emails/run × 48 runs/day = 9,600 emails/day = $115/day worst case if every email is full size. Realistically most emails are <1k tokens and we'll see $5-10/day at scale.

If cost becomes a concern: drop the body truncation from 12000 to 4000 chars, or pre-filter on subject before calling the model.

## What's next (deferred from this pass)

- **Wire signals into Stale Targets** — price-drop signals in the last 7 days should boost a competitor listing's acquisition score (it's the explicit "this seller is motivated" signal Mark asked for).
- **Sender auto-classification** — when a new sender lands, auto-classify (marketplace / broker / auctioneer / mail-only) via a follow-up LLM call so the senders table is curated rather than just timestamped.
- **Dashboard** — small Nova page showing what we're capturing: top senders, signal counts by event type, recent price drops, recent featured lots.
