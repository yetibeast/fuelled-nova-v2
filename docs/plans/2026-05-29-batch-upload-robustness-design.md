# Batch upload robustness — parse → review → price

**Date:** 2026-05-29
**Trigger:** Harsh's `Optimum Tech 2026-05-26.xlsx` batch upload reported "14/14 priced, $0/$0". The parser slurped a form-style sheet (company name, a date cell, the header row "Type of Equipment", bare type words) into 14 garbage line items, priced them silently, and showed a false "complete." Known failure: the system must *handle* messy real-world spreadsheets, not just patch one detection rule.

## What already shipped (the prior fix)
- `_detect_columns` no longer lets one column claim two fields.
- `_try_schema_parse` requires a confident header (title + ≥1 identity field); low-confidence layouts route to the existing LLM extractor.
- Empty/$0 valuations count as **failed**, not completed.

Those make extraction better and reporting honest. They do **not** add a human checkpoint — this design does.

## Decision
Insert a **human review step between parse and price**. Read-only preview with row-drop only — no inline cell editing, no column remapping (YAGNI: the failure was *wholesale* garbage, and the robust path is the LLM extractor, which has no columns to remap).

## Data flow
```
1. POST /batch/start (file)   → job_id; background parse ONLY
   status: parsing → awaiting_review   (job holds parsed `items`)
2. Frontend polls, sees awaiting_review, renders items table
   (title · category · key specs), every row checked by default
3. User unchecks junk → POST /batch/{job_id}/price { items: [kept] }
   status: running → completed   (existing _price_batch_async reused)
4. Frontend polls → Batch Complete (honest: only real rows counted)
```

## Backend (`backend/app/api/batch.py`)
- `_parse_then_price` → `_parse_only`: parse, set `status="awaiting_review"`, `job["items"]=[…]`, stop. Parse logic unchanged.
- New `POST /batch/{job_id}/price`: body = kept `items` (read-only preview ⇒ identical to parsed minus drops; `BatchItem` re-validates). Unknown job → 404. Empty list → 400. Flips job to `running`, calls existing `_price_batch_async`.
- New job status `awaiting_review`; job dict gains `items`.
- **Client sends kept items** (not indices): decouples the two phases from the 1-hour in-memory job TTL, frontend already holds the list, `BatchItem` is the same guard the sync path uses.

### Left unchanged (surgical)
Parse logic, sync `/batch/upload` and `/batch` JSON endpoints, `_price_batch_async`, export, report.

## Frontend (`frontend/nova-app/components/pricing/batch-upload.tsx`)
One new branch on `awaiting_review`: poll loop stops, stashes `items`, renders a compact review table with a checkbox per row (default checked). Header: "Extracted N items — uncheck anything that isn't equipment, then price." Buttons: "Price N selected items" (disabled at 0) and "Cancel / upload another." On price → `POST /batch/{job_id}/price {items: kept}` → resume existing polling for the pricing phase. New state: `reviewItems`, `selected`; new api wrapper `priceBatchItems()`.

## Error handling
- Parse fails / 0 items → `status=failed`, `job["error"]` → frontend shows it (unchanged).
- Review session expired (TTL) → price endpoint 404 → "session expired, re-upload."
- All rows deselected → button disabled client-side; server rejects empty list with 400.
- Per-item / empty valuation → already handled by prior fix.

## Testing
- **Backend (TDD):** parse-only sets `awaiting_review` + `items`; price endpoint prices only kept items; unknown job → 404; empty list → 400. Reuses `monkeypatch run_pricing` pattern.
- **Frontend (no harness):** run the app against the reconstructed Optimum-Tech-shape sheet; confirm junk rows show in review, drop, and only real rows price.

## Definition of done
Backend tests green · app manually verified · `docs/release-notes/2026-05-29.md` rev notice drafted for Curtis · merge to `main` · deploy from main.
