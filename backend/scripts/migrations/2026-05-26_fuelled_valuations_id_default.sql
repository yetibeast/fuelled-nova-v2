-- 2026-05-26: Restore fuelled_valuations.id DEFAULT gen_random_uuid().
--
-- Root cause: same pattern as 2026-04-23_fix_scrape_targets_id_default.sql.
-- The fuelled_valuations table was created via `_VALUATIONS_DDL` in
-- backend/app/api/fuelled_coverage.py with `id UUID PRIMARY KEY` and no default.
-- CREATE TABLE IF NOT EXISTS means later schema changes never propagate.
--
-- Symptom: the 2026-05-20 Tier 1 backfill (backfill_tier1_pricing.py) had to
-- supply str(uuid_lib.uuid4()) explicitly for every row. New writers from
-- /api/v2/price (and the future background worker) must not have to know that.
-- Restoring the default makes the column behave as documented.
--
-- Safe to apply on a live table: ALTER COLUMN … SET DEFAULT never rewrites rows.
-- Idempotent: re-running is a metadata-only no-op on Postgres >= 11.
--
-- Apply on Railway prod DB:
--   psql $DATABASE_URL -f backend/scripts/migrations/2026-05-26_fuelled_valuations_id_default.sql

ALTER TABLE fuelled_valuations ALTER COLUMN id SET DEFAULT gen_random_uuid();
