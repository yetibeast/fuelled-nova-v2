# Competitive Stale Inventory Acquisition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn stale competitor inventory into a ranked acquisition workflow with a durable admin queue and draft Fuelled listing packets.

**Architecture:** Keep raw stale detection in the existing competitive read path, but move acquisition workflow state into a separate app-owned Postgres database on Railway. Fix the stale query first, add a ranked `stale-targets` feed, then layer an admin promotion/status/draft workflow on top.

**Tech Stack:** FastAPI, SQLAlchemy async, Postgres via `asyncpg`, React/TypeScript, Tailwind v4

**Spec:** `docs/superpowers/specs/2026-04-15-competitive-stale-acquisition-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/config.py` | Add `STATE_DATABASE_URL` |
| Create | `backend/app/db/state_session.py` | Sidecar state DB engine/session |
| Create | `backend/app/competitive_acquisition.py` | Thresholds, scoring, promotability, draft builder |
| Modify | `backend/app/api/competitive.py` | Fix stale queries and add `GET /api/competitive/stale-targets` |
| Create | `backend/app/api/competitive_queue.py` | Admin promotion, queue summary, status, draft endpoints |
| Modify | `backend/app/main.py` | Register new router |
| Create | `backend/tests/test_competitive_acquisition.py` | Endpoint and queue tests |
| Modify | `backend/tests/conftest.py` | Seed competitor stale listings and mock state store |
| Modify | `backend/tests/test_auth_guards.py` | Cover new admin endpoints |
| Modify | `frontend/nova-app/lib/api.ts` | Add fetch/mutate wrappers |
| Create | `frontend/nova-app/components/competitive/stale-targets.tsx` | Ranked stale candidate table |
| Create | `frontend/nova-app/components/competitive/acquisition-queue.tsx` | Admin queue table |
| Modify | `frontend/nova-app/app/(app)/competitive/page.tsx` | Render new stale targets + queue UI |

---

## Task 1: Add state DB plumbing

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/db/state_session.py`

- [ ] Add `STATE_DATABASE_URL` to `config.py` as a dedicated env var for the app-owned Railway Postgres state DB.
- [ ] Create `state_session.py` with a dedicated async SQLAlchemy engine and `get_state_session()` context manager.
- [ ] Use the existing `asyncpg` stack; no new DB driver dependency is needed.
- [ ] Keep the existing `DATABASE_URL` session unchanged; stale detection still reads from the shared listings source.
- [ ] Do not allow `STATE_DATABASE_URL` to default to `DATABASE_URL`.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && python3 -m pytest tests/test_nonfunctional.py -v
```

**Expected**

- Existing nonfunctional tests still pass.

---

## Task 2: Seed stale competitor listings and state-store mocks

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] Extend the in-memory listing seeds with competitor rows that cover:
  - stale promotable listing
  - stale but auction-only listing
  - recent competitor listing
  - Fuelled stale listing that must be excluded
- [ ] Add in-memory stores for:
  - `competitive_acquisition_targets`
  - `competitive_acquisition_events`
- [ ] Add mock SQL handlers for:
  - fixed stale summary counts
  - `GET /competitive/stale-targets` peer/score query
  - acquisition target inserts, reads, updates
- [ ] Patch both `get_session()` and `get_state_session()` in the new modules.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && python3 -m pytest tests/conftest.py -q
```

**Expected**

- No import errors from the new state-session module.

---

## Task 3: Write failing backend tests first

**Files:**
- Create: `backend/tests/test_competitive_acquisition.py`
- Modify: `backend/tests/test_auth_guards.py`

- [ ] Add tests for `GET /api/competitive/summary` proving stale counts exclude Fuelled rows.
- [ ] Add tests for `GET /api/competitive/stale-targets` proving:
  - results are competitor-only
  - results include `acquisition_score`
  - `promotable_only=true` removes auction-only rows
- [ ] Add admin tests for:
  - `GET /api/admin/competitive/acquisition/summary`
  - `GET /api/admin/competitive/acquisition/targets`
  - `POST /api/admin/competitive/acquisition/promote`
  - `POST /api/admin/competitive/acquisition/{id}/status`
  - `POST /api/admin/competitive/acquisition/{id}/draft`
- [ ] Add auth-guard coverage for the new admin endpoints to `test_auth_guards.py`.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && PYTHONPATH=. python3 -m pytest tests/test_competitive_acquisition.py tests/test_auth_guards.py -v
```

**Expected**

- FAIL with route-not-found or missing-module errors.

---

## Task 4: Implement acquisition domain logic

**Files:**
- Create: `backend/app/competitive_acquisition.py`

- [ ] Add category-threshold mapping helper.
- [ ] Add source-policy helper that marks auction-like sources as non-promotable.
- [ ] Add score calculator returning:
  - `days_listed`
  - `stale_threshold_days`
  - `peer_median`
  - `peer_count`
  - `acquisition_score`
  - `promotable`
  - `reason`
- [ ] Add draft-payload builder used by the admin queue endpoint.
- [ ] Keep this module framework-light; no FastAPI imports here.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && PYTHONPATH=. python3 -m pytest tests/test_competitive_acquisition.py -k "stale_targets" -v
```

**Expected**

- Still failing, but now on missing endpoint logic instead of missing scoring helpers.

---

## Task 5: Fix stale queries and add ranked stale-targets feed

**Files:**
- Modify: `backend/app/api/competitive.py`

- [ ] Fix the existing stale summary query so it includes `LOWER(source) != 'fuelled'`.
- [ ] Fix the existing stale list query so it includes `LOWER(source) != 'fuelled'`.
- [ ] Add `GET /api/competitive/stale-targets`.
- [ ] Reuse existing auth level from `competitive.py`: authenticated user, not admin-only.
- [ ] Compute ranking fields from raw listings plus the acquisition-domain helper.
- [ ] Support `promotable_only`, `min_score`, and `limit`.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && PYTHONPATH=. python3 -m pytest tests/test_competitive_acquisition.py -k "summary or stale_targets" -v
```

**Expected**

- Summary and stale-target tests pass.

---

## Task 6: Add admin acquisition queue endpoints

**Files:**
- Create: `backend/app/api/competitive_queue.py`
- Modify: `backend/app/main.py`

- [ ] Create state-table bootstrap logic in `competitive_queue.py`.
- [ ] Run idempotent `CREATE TABLE IF NOT EXISTS` only against `STATE_DATABASE_URL`, never against the shared scrape DB.
- [ ] Use `_require_admin` for every endpoint in this router.
- [ ] Implement:
  - `GET /api/admin/competitive/acquisition/summary`
  - `GET /api/admin/competitive/acquisition/targets`
  - `POST /api/admin/competitive/acquisition/promote`
  - `POST /api/admin/competitive/acquisition/{target_id}/status`
  - `POST /api/admin/competitive/acquisition/{target_id}/draft`
- [ ] On promote:
  - re-read the source listing from `listings`
  - recompute score/promotability
  - reject non-promotable candidates with `409`
  - snapshot source fields into the state store
- [ ] On status update:
  - validate allowed statuses
  - update `updated_at`
  - append event row
- [ ] Register the new router in `main.py`.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && PYTHONPATH=. python3 -m pytest tests/test_competitive_acquisition.py tests/test_auth_guards.py -v
```

**Expected**

- Backend tests for the new queue endpoints pass.

---

## Task 7: Add frontend API wrappers

**Files:**
- Modify: `frontend/nova-app/lib/api.ts`

- [ ] Add:
  - `fetchCompetitiveStaleTargets()`
  - `fetchAcquisitionSummary()`
  - `fetchAcquisitionTargets()`
  - `promoteAcquisitionTarget()`
  - `updateAcquisitionStatus()`
  - `generateAcquisitionDraft()`
- [ ] Keep these on `/api/...` paths so the existing Next.js rewrite handles them.
- [ ] Follow the existing auth-header patterns in `lib/api.ts`.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/frontend/nova-app && npm run lint
```

**Expected**

- TypeScript/lint passes or only shows pre-existing issues unrelated to these wrappers.

---

## Task 8: Add stale-targets table UI

**Files:**
- Create: `frontend/nova-app/components/competitive/stale-targets.tsx`
- Modify: `frontend/nova-app/app/(app)/competitive/page.tsx`

- [ ] Create a ranked stale-targets table matching the existing competitive table style.
- [ ] Show:
  - title
  - category
  - asking price
  - days listed
  - threshold
  - peer median
  - score
  - source
- [ ] Add row actions:
  - open source URL
  - promote for admin users when `promotable`
- [ ] Load this table automatically with the page instead of hiding it behind the "Load Analysis" button.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/frontend/nova-app && npm run lint
```

**Expected**

- New table component compiles cleanly.

---

## Task 9: Add admin acquisition queue UI

**Files:**
- Create: `frontend/nova-app/components/competitive/acquisition-queue.tsx`
- Modify: `frontend/nova-app/app/(app)/competitive/page.tsx`

- [ ] Create a second section for promoted targets.
- [ ] Show queue summary counts near the top for admins.
- [ ] Render queue rows with:
  - status
  - score
  - asking price
  - peer median
  - source URL
  - actions to change status and generate draft
- [ ] Keep the UI read-only for non-admin users.
- [ ] Do not add a separate route yet; keep this inside the existing `/competitive` page.

**Run**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/frontend/nova-app && npm run lint
```

**Expected**

- Competitive page compiles with both sections.

---

## Task 10: Full verification

**Files:**
- No new files

- [ ] Run backend test file:

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/backend && PYTHONPATH=. python3 -m pytest tests/test_competitive_acquisition.py tests/test_auth_guards.py -v
```

- [ ] Run frontend lint:

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2/frontend/nova-app && npm run lint
```

- [ ] Manual browser verification:
  - stale summary count excludes Fuelled rows
  - stale-targets list loads on `/competitive`
  - auction-only rows are visible but not promotable
  - admin can promote a candidate
  - promoted candidate appears in acquisition queue
  - status update persists
  - draft packet generation returns a populated payload

---

## Notes for Implementation

- Do not write acquisition flags back onto `listings`.
- Do not publish directly to Fuelled in this phase.
- Do not call pricing-v2 from the stale-target feed in V1; keep the feed fast and deterministic.
- Keep auction-source rules and threshold mapping code-defined for now; no admin editor yet.

Plan complete and saved to `docs/superpowers/plans/2026-04-15-competitive-stale-acquisition.md`.
