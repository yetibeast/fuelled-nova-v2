-- 2026-05-26: pricing_runs — bulk pricing job tracking for the background worker.
--
-- Why: Phase B background worker (and ad-hoc batch_runner CLI) will price the
-- 65K unpriced listing backlog in chunks. Each invocation gets a run_id so we
-- can attribute every fuelled_valuations row back to the batch that produced
-- it, monitor throughput/cost, and resume on failure.
--
-- One row per invocation. Status transitions: running -> succeeded | failed | partial.
-- methodology_version is the engine_version slug at run time (e.g. "nova_v2"),
-- so we can tell which engine produced a given batch even after we cut a v3.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + IF NOT EXISTS indexes.

CREATE TABLE IF NOT EXISTS pricing_runs (
    run_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'running',
    listings_total      INTEGER NOT NULL DEFAULT 0,
    listings_succeeded  INTEGER NOT NULL DEFAULT 0,
    listings_failed     INTEGER NOT NULL DEFAULT 0,
    methodology_version TEXT,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_pricing_runs_started_at
  ON pricing_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pricing_runs_status
  ON pricing_runs (status);
