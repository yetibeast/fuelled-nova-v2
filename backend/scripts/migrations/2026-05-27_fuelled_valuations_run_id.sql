-- 2026-05-27: Add run_id FK from fuelled_valuations -> pricing_runs.
--
-- Why: the bulk runners (tanks today, all families soon) need to attribute
-- every priced row back to the batch that produced it, so we can monitor
-- per-run throughput/cost and delete a bad run cleanly. The pricing_runs
-- table landed on 2026-05-26 but the FK column on fuelled_valuations was
-- missed in that migration set. admin_pricing_tanks.py INSERT relies on
-- this column.
--
-- Safe to apply on live table: ADD COLUMN with no default is metadata-only
-- on Postgres >= 11. No backfill needed — existing rows get NULL (pre-batch-
-- runner valuations from manual/legacy paths).
--
-- Idempotent: ADD COLUMN IF NOT EXISTS.
--
-- Apply on Railway prod DB:
--   psql $DATABASE_URL -f backend/scripts/migrations/2026-05-27_fuelled_valuations_run_id.sql

ALTER TABLE fuelled_valuations
  ADD COLUMN IF NOT EXISTS run_id UUID;

-- Soft FK only — pricing_runs is reference data, no cascade desired.
-- (A bad delete on pricing_runs shouldn't nuke produced valuations.)
CREATE INDEX IF NOT EXISTS idx_fuelled_valuations_run_id
  ON fuelled_valuations (run_id)
  WHERE run_id IS NOT NULL;
