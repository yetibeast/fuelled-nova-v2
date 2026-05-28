-- 2026-05-26: Pricing Review columns on fuelled_valuations.
--
-- Why: Phase B1 Pricing Review UI needs per-valuation review state distinct
-- from confidence/status. Curtis/Mark will eyeball low-confidence outputs in
-- "pending oldest first" order, mark them approved or needing rework. The
-- existing `confidence` column is the engine's self-assessment; `review_status`
-- is the human's decision.
--
-- Values for review_status:
--   * 'pending'   — default; awaiting human review
--   * 'approved'  — reviewer confirmed
--   * 'rejected'  — reviewer flagged for rework; hold from publication
--   * 'auto'      — engine ran without human pass (high-confidence skip-review path)
--
-- The composite index supports the Review UI's main query pattern:
--   SELECT ... WHERE review_status = 'pending' ORDER BY created_at ASC LIMIT N.
--
-- Safe to apply on a live table: ADD COLUMN with no DEFAULT (or a constant
-- DEFAULT) is metadata-only on Postgres >= 11. CREATE INDEX on ~1,200 rows is
-- effectively instant.
-- Idempotent: IF NOT EXISTS throughout.
--
-- Apply on Railway prod DB:
--   psql $DATABASE_URL -f backend/scripts/migrations/2026-05-26_fuelled_valuations_review_columns.sql

ALTER TABLE fuelled_valuations
  ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS reviewed_by   TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS review_notes  TEXT;

CREATE INDEX IF NOT EXISTS idx_fuelled_valuations_review_pending
  ON fuelled_valuations (review_status, created_at);
