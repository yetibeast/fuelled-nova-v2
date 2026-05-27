-- 2026-05-27: Freshness + run-audit additions for the recurring enrichment pipeline.
--
-- Layers on top of 2026-05-27_seller_contact_enrichment.sql (which created
-- seller_contact_enrichment + buyer_targets and imported the May 10 workbook).
--
-- What this adds:
--   * Freshness columns on seller_contact_enrichment so the recurring loop
--     knows when each seller was last researched, how many attempts, and
--     why the last attempt failed (if it did).
--   * enrichment_runs: per-batch audit row written by run_enrichment.py.
--     One row per cron invocation; tracks provider chain, counts, cost.
--   * enrichment_queue: a *view* (not a table) so it always reflects current
--     state. Lists sellers in `listings` that are either never researched
--     or stale (>90d), capped at 3 attempts, ranked by listing_volume.
--
-- Additive-only. No table renames. No data migration required.

ALTER TABLE seller_contact_enrichment
  ADD COLUMN IF NOT EXISTS last_researched_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS research_attempts   INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_research_error TEXT,
  ADD COLUMN IF NOT EXISTS confidence_overall  TEXT;


CREATE TABLE IF NOT EXISTS enrichment_runs (
    run_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    trigger           TEXT NOT NULL,          -- 'cron-weekly' | 'cron-quarterly' | 'manual'
    provider_chain    TEXT NOT NULL,          -- e.g. 'claude_parallel'
    sellers_total     INTEGER NOT NULL DEFAULT 0,
    sellers_succeeded INTEGER NOT NULL DEFAULT 0,
    sellers_failed    INTEGER NOT NULL DEFAULT 0,
    contacts_added    INTEGER NOT NULL DEFAULT 0,
    cost_usd          NUMERIC(8,3) DEFAULT 0,
    notes             TEXT
);

CREATE INDEX IF NOT EXISTS idx_enrichment_runs_started_at
    ON enrichment_runs (started_at DESC);


-- enrichment_queue: live view, never materialized. Recomputed every SELECT.
--
-- Inclusion rule (rows the recurring runner should pick up):
--   * Seller appears in listings (non-empty seller_name).
--   * AND (never researched OR last_researched_at < NOW() - 90d).
--   * AND attempts < 3 (give up after 3 failures, surface via /status).
--
-- Each row is per (seller_name, source). One seller scraped from two sources
-- yields two queue rows (e.g. same dealer on AllSurplus + BidSpotter).
CREATE OR REPLACE VIEW enrichment_queue AS
WITH seller_summary AS (
    SELECT l.seller_name,
           l.source,
           COUNT(*) AS listing_volume,
           MAX(l.last_seen) AS last_seen
    FROM listings l
    WHERE l.seller_name IS NOT NULL
      AND l.seller_name <> ''
    GROUP BY l.seller_name, l.source
),
existing_enrichment AS (
    SELECT seller_name,
           source,
           MAX(last_researched_at) AS last_researched_at,
           MAX(research_attempts)  AS attempts
    FROM seller_contact_enrichment
    GROUP BY seller_name, source
)
SELECT s.seller_name,
       s.source,
       s.listing_volume,
       s.last_seen,
       e.last_researched_at,
       COALESCE(e.attempts, 0) AS attempts,
       CASE
         WHEN e.last_researched_at IS NULL THEN 'never'
         WHEN e.last_researched_at < NOW() - INTERVAL '90 days' THEN 'stale'
         ELSE 'fresh'
       END AS freshness
FROM seller_summary s
LEFT JOIN existing_enrichment e
       ON e.seller_name = s.seller_name
      AND (e.source = s.source OR e.source IS NULL)
WHERE (e.last_researched_at IS NULL
       OR e.last_researched_at < NOW() - INTERVAL '90 days')
  AND COALESCE(e.attempts, 0) < 3
ORDER BY s.listing_volume DESC;
