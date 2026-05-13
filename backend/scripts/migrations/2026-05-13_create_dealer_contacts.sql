-- 2026-05-13: dealer_contacts — reference table for enriched seller contact info.
--
-- Why: Kijiji exposes seller name + dealer profile URL in the listing page Apollo
-- state (already captured), but phone/email are gated behind a JS-revealed button
-- + reCAPTCHA on the dealer profile page (toggleEnableRecaptchaCheckPhoneNumberReveal).
-- We can't scrape those headlessly. Instead we enrich the top dealers via public-web
-- research and store the contacts here. Same approach we used for the ANCO unmask.
--
-- This table is the source of truth. It survives any scraper UPSERT on listings.
--
-- Usage tonight (pragmatic): a sync script writes from here into
-- listings.event_contact_* so the existing /competitive/stale-targets.csv writer
-- surfaces the contacts without code change. Idempotent.
--
-- Usage tomorrow (clean): /competitive endpoint LEFT JOINs dealer_contacts and
-- COALESCEs over event_contact_*. The listings overload becomes unnecessary.

CREATE TABLE IF NOT EXISTS dealer_contacts (
    seller_name        TEXT NOT NULL,
    source             TEXT NOT NULL,
    contact_name       TEXT,
    contact_email      TEXT,
    contact_phone      TEXT,
    website            TEXT,
    address            TEXT,
    notes              TEXT,
    enrichment_source  TEXT,
    enriched_by        TEXT,
    enriched_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (seller_name, source)
);

CREATE INDEX IF NOT EXISTS idx_dealer_contacts_source ON dealer_contacts (source);
