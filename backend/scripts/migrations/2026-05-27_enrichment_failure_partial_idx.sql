-- 2026-05-27: Partial unique index for failure-marker rows.
--
-- Bug C2: the existing uq_seller_contact_enrichment_key index covers
-- (seller_name, source, contact_email), but Postgres treats NULL as
-- distinct in unique indexes. The runner's _MARK_FAILURE_SQL inserts
-- a marker row with contact_email = NULL whenever the provider returns
-- no contacts or errors; every retry created a new row instead of
-- bumping research_attempts on the existing one.
--
-- This partial index gives a single conflict target for marker rows.
-- It scopes to WHERE contact_email IS NULL so it does not interfere
-- with the existing full key for real-contact rows.
--
-- Additive-only. Idempotent via IF NOT EXISTS.

CREATE UNIQUE INDEX IF NOT EXISTS uq_seller_contact_enrichment_failure_marker
    ON seller_contact_enrichment (seller_name, source)
    WHERE contact_email IS NULL;
