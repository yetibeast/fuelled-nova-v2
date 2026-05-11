-- 2026-05-10: Catch-all competitor mailout capture.
--
-- Mark's "Next agentic tool" email (2026-04-07) flagged a need for the team
-- to subscribe a single inbox to competitor mailing lists — covers companies
-- with no online marketplace (mail-only brokers/auctioneers) as well as the
-- marketplaces we already scrape. We pull every inbound email, store the raw
-- content, and run an LLM extractor to surface structured signals (new
-- listings, price drops, sold notifications, auction reminders, featured
-- lots, urgency markers).
--
-- Sender-agnostic by design — no hand-coded parsers per marketplace.
-- LLM does classification + extraction, raw email kept for re-processing.
--
-- Three tables:
--   competitor_emails       -- one row per inbound message (raw capture)
--   competitor_email_signals -- one row per extracted listing/event
--   competitor_email_senders -- sender registry (who's writing to us)
--
-- All FKs nullable / ON DELETE CASCADE so we can re-extract without losing
-- raw data, and re-classify senders without dropping signals.

CREATE TABLE IF NOT EXISTS competitor_emails (
    id                  TEXT PRIMARY KEY,
    gmail_message_id    TEXT NOT NULL UNIQUE,
    gmail_thread_id     TEXT,
    sender_email        TEXT NOT NULL,
    sender_domain       TEXT NOT NULL,
    sender_name         TEXT,
    subject             TEXT,
    received_at         TIMESTAMPTZ NOT NULL,
    snippet             TEXT,
    body_text           TEXT,
    body_html           TEXT,
    raw_headers         JSONB,
    extracted_at        TIMESTAMPTZ,
    extraction_status   TEXT NOT NULL DEFAULT 'pending'
                        CHECK (extraction_status IN ('pending','success','failed','skipped')),
    extraction_error    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_competitor_emails_received_at
    ON competitor_emails (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_emails_sender_domain
    ON competitor_emails (sender_domain);
CREATE INDEX IF NOT EXISTS idx_competitor_emails_extraction_status
    ON competitor_emails (extraction_status)
    WHERE extraction_status = 'pending';


CREATE TABLE IF NOT EXISTS competitor_email_signals (
    id                      TEXT PRIMARY KEY,
    email_id                TEXT NOT NULL REFERENCES competitor_emails(id) ON DELETE CASCADE,
    event_type              TEXT NOT NULL
                            CHECK (event_type IN ('new_listing','price_drop','auction_reminder',
                                                  'sold_notification','featured','newsletter','other')),
    listing_title           TEXT,
    listing_url             TEXT,
    listing_external_id     TEXT,
    listing_category_hint   TEXT,
    listing_location        TEXT,
    asking_price            NUMERIC,
    previous_price          NUMERIC,
    currency                TEXT,
    seller_hint             TEXT,
    urgency_signal          TEXT,
    matched_listing_id      TEXT,
    raw_extracted           JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_email_id
    ON competitor_email_signals (email_id);
CREATE INDEX IF NOT EXISTS idx_signals_event_type
    ON competitor_email_signals (event_type);
CREATE INDEX IF NOT EXISTS idx_signals_listing_url
    ON competitor_email_signals (listing_url)
    WHERE listing_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_signals_matched_listing
    ON competitor_email_signals (matched_listing_id)
    WHERE matched_listing_id IS NOT NULL;


CREATE TABLE IF NOT EXISTS competitor_email_senders (
    sender_email    TEXT PRIMARY KEY,
    sender_domain   TEXT NOT NULL,
    display_name    TEXT,
    first_seen_at   TIMESTAMPTZ NOT NULL,
    last_seen_at    TIMESTAMPTZ NOT NULL,
    email_count     INTEGER NOT NULL DEFAULT 0,
    classified_as   TEXT
                    CHECK (classified_as IS NULL OR classified_as IN
                          ('marketplace','broker','auctioneer','manufacturer',
                           'newsletter','industry_news','unknown')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_senders_domain
    ON competitor_email_senders (sender_domain);
CREATE INDEX IF NOT EXISTS idx_senders_classified
    ON competitor_email_senders (classified_as);
