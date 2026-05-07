-- 2026-04-23: Fix scrape_targets.id missing DEFAULT gen_random_uuid() on prod.
--
-- Root cause: the table was created before DEFAULT gen_random_uuid() was added
-- to _INIT_SQLS in admin_scrapers.py. CREATE TABLE IF NOT EXISTS is a no-op on
-- existing tables, so the schema definition change never propagated to prod.
-- Result: POST /api/admin/scrapers returned 500 when the INSERT omitted id.
--
-- Commit 52a1e18 patched the immediate breakage by passing gen_random_uuid()
-- explicitly in the INSERT. This migration closes the underlying schema drift so
-- the column behaves as documented and any future INSERT path is covered.
--
-- Also covers scrape_runs.id, which has the same drift (same table creation
-- epoch, same CREATE TABLE IF NOT EXISTS no-op).
--
-- Safe to apply on a live table: ALTER COLUMN … SET DEFAULT never rewrites rows.
-- Idempotent: running twice is harmless (SET DEFAULT is not conditional, but
-- the second run is a metadata-only no-op on Postgres >= 11).
--
-- Apply on Railway prod DB:
--   psql $DATABASE_URL -f backend/scripts/migrations/2026-04-23_fix_scrape_targets_id_default.sql

ALTER TABLE scrape_targets ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE scrape_runs    ALTER COLUMN id SET DEFAULT gen_random_uuid();
