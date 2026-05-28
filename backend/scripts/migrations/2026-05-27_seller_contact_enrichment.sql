-- 2026-05-27: Seller-side + buyer-side contact enrichment from the
-- May 10 supply-targets workbook (docs/supply-targets/supply_targets_enriched_2026-05-10.xlsx).
--
-- Mirrors the existing dealer_contacts pattern (2026-05-13) but split into two
-- tables because the workbook covers both sides of the mailout: supply-side
-- enrichment that needs to JOIN to listings, and buy-side companies that
-- never appear in listings at all.
--
-- ── seller_contact_enrichment ─────────────────────────────────────────
-- Joins to listings.seller_name (case-sensitive, exact match — same as
-- dealer_contacts). When `source` is NULL the enrichment applies to every
-- source for that seller_name; when set, it scopes to one platform (used
-- for the LS event-manager rows which apply specifically to AllSurplus).
--
-- Consumed by /api/admin/mailout/sellers.csv via LEFT JOIN. The endpoint
-- surfaces the enriched contact fields alongside the scraper-captured
-- event_contact_* values so reviewers see both signals.
--
-- ── buyer_targets ─────────────────────────────────────────────────────
-- Buy-side companies (O&G operators, midstream, etc.) that purchase from
-- secondary markets. Does NOT join to listings — these are demand-side
-- targets, not sellers. Consumed by /api/admin/mailout/buyers.csv.
--
-- Each buyer-contact row carries both the company-level metadata
-- (vertical, ticker, HQ, basin, scale, capex_driver, suppliers_page) and
-- the contact-level fields (name, title, email, linkedin, confidence,
-- location, outreach_notes). Companies without a known contact get a
-- single row with contact fields NULL.
--
-- Both tables are additive (CREATE TABLE IF NOT EXISTS) and idempotent
-- via the import script's ON CONFLICT DO UPDATE clauses.

CREATE TABLE IF NOT EXISTS seller_contact_enrichment (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_name         TEXT NOT NULL,
    source              TEXT,
    contact_name        TEXT,
    contact_title       TEXT,
    contact_email       TEXT,
    contact_phone       TEXT,
    contact_linkedin    TEXT,
    contact_confidence  TEXT,
    location            TEXT,
    outreach_notes      TEXT,
    enrichment_source   TEXT NOT NULL DEFAULT 'may10_workbook',
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique on (seller_name, source, contact_email). NULLs in source or email
-- are treated as distinct rows by Postgres unique constraints by default,
-- which is what we want — multiple unknown-email contacts for one seller
-- shouldn't collapse to one row.
CREATE UNIQUE INDEX IF NOT EXISTS uq_seller_contact_enrichment_key
    ON seller_contact_enrichment (seller_name, source, contact_email);

CREATE INDEX IF NOT EXISTS idx_seller_contact_enrichment_seller
    ON seller_contact_enrichment (seller_name);


CREATE TABLE IF NOT EXISTS buyer_targets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vertical            TEXT,
    company             TEXT NOT NULL,
    ticker              TEXT,
    hq                  TEXT,
    basin               TEXT,
    scale               TEXT,
    capex_driver        TEXT,
    suppliers_page      TEXT,
    contact_name        TEXT,
    contact_title       TEXT,
    contact_email       TEXT,
    contact_linkedin    TEXT,
    contact_confidence  TEXT,
    location            TEXT,
    outreach_notes      TEXT,
    enrichment_source   TEXT NOT NULL DEFAULT 'may10_workbook',
    imported_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_buyer_targets_key
    ON buyer_targets (company, contact_email);

CREATE INDEX IF NOT EXISTS idx_buyer_targets_company
    ON buyer_targets (company);

CREATE INDEX IF NOT EXISTS idx_buyer_targets_vertical
    ON buyer_targets (vertical);
