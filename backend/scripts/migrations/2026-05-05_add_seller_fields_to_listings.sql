-- 2026-05-05: Add seller fields to listings for AllSurplus supply targeting.
-- Mark Le Dain's "List of Supply Targets" ask (2026-05-05). Phase 1: public capture.
--
-- All four columns are nullable and additive. Safe to apply on a live table:
-- IF NOT EXISTS guards the re-run case. Index on seller_source_id supports the
-- supply-targets aggregation query (GROUP BY source, seller_source_id).
--
-- Apply on Railway prod DB:
--   railway ssh --service backend "psql $DATABASE_URL -f /app/scripts/migrations/2026-05-05_add_seller_fields_to_listings.sql"
-- or via the runner volume / direct psql connection.

ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_source_id      TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_name           TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_account_type   TEXT;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS seller_other_assets_url TEXT;

CREATE INDEX IF NOT EXISTS idx_listings_seller_source
    ON listings (source, seller_source_id)
    WHERE seller_source_id IS NOT NULL;
