# Session handoff — 2026-05-27 (into early 05-28)

For the next agent picking up Fuelled-Nova. Read this top-to-bottom before touching anything; it captures state, gotchas, and how this session worked so you can continue without re-discovering it.

---

## TL;DR

Started from two Mark complaints (EOG analysis pulling Canadian comps; a batch report that mostly failed). Ended the night with a consolidated `main` that matches prod, deploy discipline locked in CLAUDE.md, seller mailout coverage lifted 24%→72%, and a clean test signal. 13 of 15 tracked tasks closed. Everything shipped is verified with evidence. Nothing is half-merged.

**Current prod HEAD = `main` HEAD = `f4c4d8d`.** main now equals what's deployed (this was NOT true at session start — see "Git consolidation").

---

## What shipped to prod tonight (all on `main`, deployed, verified)

| Change | Commit | Why | Verified |
|--------|--------|-----|----------|
| Batch per-item timeout 60→120s | `867473c` | Mark's EOG batch failed 93/113 items at the 60s `asyncio.wait_for` wall | `grep timeout= /app/app/api/batch.py` in container = 120 |
| Country filter on `search_comparables` | `26c2be2` | Mark's EOG complaint — US deals pulled CA comps; tool had no country knob | 3 tests RED→GREEN; tiered country detection (country col → ISO suffix → state/prov codes → full names) |
| Frontend `NovaApiError` mapping | `4324651` | Backend shipped structured errors (b7a3b29 earlier) but frontend never read them → users still saw "Something went wrong" | committed; was uncommitted-on-main cruft |
| Tier 2 family rulesets ×5 | `3515d19`,`69b6cb6`,`b0a8d4e`,`0c89f88`,`562f8b9` | heater/treater/knockouts/dehydrator/meter-runs each get dedicated RCN brackets + curves | merged clean; **shipped WITHOUT per-family sample-row review — Curtis accepted that risk explicitly** |
| Runner Anthropic per-call timeout | `2ee21f1` | A backfill hung 36 min on one Anthropic call; SDK timeout never fired | 13 tests green; `asyncio.wait_for(timeout=120)` in claude_parallel |
| C2 + C2-followup upsert fixes | (in intel chain) + `732aaf4` | failure markers duplicated (NULL-distinct); then success-rows-with-no-email collided with the partial index | 9 Postgres integration tests; **0 IntegrityErrors across the 168-seller backfill** |
| Recurring enrichment pipeline + `/api/v2/intel/{status,queue}` | `a96b80c` + intel chain | autonomous seller-contact enrichment | endpoints return 401 (registered); migrations applied to prod DB |
| Test event-loop isolation | `f4c4d8d` | suite was order-dependent: `asyncio.run()` poisoned later `get_event_loop()` tests | full suite 49→14 failed (the 14 are pre-existing, unrelated) |
| CLAUDE.md §6 deploy discipline | `ab8b428` | a noon hotfix got silently stripped by an evening deploy from a different branch | doc only |

**The headline business outcome:** seller mailout coverage **24% → 72%** (214/299 seller-source pairs now have a named contact, 165 with email) for **$8.64** via one ~21-min backfill. Buyer side was already 92% (52 companies, 48 emails) from May 10 research — unchanged.

---

## Git consolidation (important context)

At session start, `main` was ~29 commits behind reality. The team had been deploying directly from feature worktrees via `railway up`, never merging back. 7 feature branches existed; their code was "live" only because the last-deployed branch (intel) happened to stack most of them.

Tonight all of it was merged into `main` in dependency order (intel chain first, then the 5 tier2/meter-runs branches — all merged CLEAN, no conflicts). **`main` now = prod.** The feature worktrees still exist under `/Users/lynch/Documents/worktrees/` but their content is all on main now; they can be pruned when convenient.

**The regression that triggered the cleanup:** the batch-timeout hotfix shipped from `hotfix/batch-timeout-120s` at noon was overwritten when the intel branch deployed in the evening (intel didn't contain it). Container silently reverted to `timeout=60`. This is why CLAUDE.md §6 now mandates deploy-from-main-only.

---

## Operational gotchas (you WILL hit these)

1. **Deploy from `backend/`, not the repo root.** `railway up` from repo root silently uploaded a stale/truncated context — build "succeeded" but the container had old code (whole-repo upload is 69M; from `backend/` it's small and correct). Always: `cd backend && railway up --service backend --detach`.
2. **Deploy from `main` only.** See CLAUDE.md §6. Merge feature branches first. After every deploy, spot-check a signature line of the previous fix (`railway ssh "grep timeout= /app/app/api/batch.py"`). Silence ≠ success.
3. **Railway link gets crossed.** The CLI link flips between `backend` and `Postgres-4SR7` depending on what you last linked. Re-link explicitly: `railway link --project fuelled-nova --environment production --service backend`.
4. **Prod DB access:** `DATABASE_URL=$(railway variables --service Postgres-4SR7 --kv | grep '^DATABASE_PUBLIC_URL=' | cut -d= -f2-)` then `/opt/homebrew/opt/postgresql@16/bin/psql "$DATABASE_URL"`. The internal `DATABASE_URL` (railway.internal host) is NOT reachable from your machine — use `DATABASE_PUBLIC_URL`.
5. **Container has no `ps`.** Inspect processes via `/proc`: `for p in $(ls /proc | grep -E '^[0-9]+$'); do cat /proc/$p/cmdline | tr '\0' ' '; done`. Check what a hung PID waits on via `/proc/<pid>/wchan` and `/proc/<pid>/net/tcp`.
6. **Local Python is 3.9; container is 3.11.** Tests run locally need `set -a && source backend/.env && set +a && PYTHONPATH=backend python3 -m pytest ...`.
7. **Gmail MCP can't fetch attachments.** Use direct OAuth + REST for anything beyond simple read/draft (see memory `feedback_prefer_oauth_over_mcp`). The 10:27am Mark screenshot is still unread for this reason — another agent owns it.
8. **Prompt cache:** `_cached_prompt` in `prompts.py` means a backend restart is needed for prompt changes (e.g. the country-filter guidance) to take effect. A deploy restarts the container, so deploys clear it.

---

## The enrichment runner (how to run a backfill)

```
cd backend && cd /Users/lynch/Documents/worktrees/fuelled-nova-v2-intel  # any worktree on main works
railway ssh "cd /app && nohup python3 -m scripts.run_enrichment \
  --provider claude_parallel --limit 200 --max-cost-usd 20 \
  --trigger backfill-LABEL > /tmp/enrich.log 2>&1 & echo started_pid=\$!"
```
- Flags: `--limit`, `--max-cost-usd`, `--trigger` (free-text audit label), `--provider {claude_parallel,mock}`, `--dry-run`. Note it's `--trigger` NOT `--mode` (the spec's `--mode` was never implemented; see commit `f9bf3b2`).
- Runner writes an `enrichment_runs` audit row up-front (`finished_at` NULL) then commits per-seller. A crash leaves a recoverable trail.
- Cost: ~$0.05-0.09/seller measured. Per-call 120s timeout now bounds hangs.
- Monitor completion by polling `SELECT ... FROM enrichment_runs WHERE trigger='LABEL' AND finished_at IS NOT NULL`.
- **~85 sellers came back "no contacts returned"** (sparse online presence — Asset Built, Martin's, Royal Auction, Alex Lyon, etc.). They'll be retried when the weekly cron is enabled (research_attempts < 3 + 90-day staleness in `enrichment_queue`).

---

## Emails + artifacts produced (yours to send/review)

- **Gmail draft** reply to Mark re: EOG/CA comps — draft ID `r-7582491760747272885`, threaded under "In that latest analysis on the EOG units". Body is non-technical per house style. NOT sent.
- `docs/mark-reply-eog-comps-2026-05-27.md` — the source draft + notes for Curtis.
- `docs/release-notes/2026-05-27.md` — rev notice: Tier 2 families.
- `docs/release-notes/2026-05-27-pricing-reliability.md` — rev notice: country filter + timeouts + backfill results (24%→72%).
- Curtis owns all sends — don't assume a notice is "out" because the file exists (CLAUDE.md §5).

---

## Open / planned (pick up here)

| Task | Status | Notes |
|------|--------|-------|
| Enable weekly enrichment cron | **NOT ready — needs deployment to container 107 first** | See the dedicated "Cron enablement — actual state" section below. The cron file is already installed on 107 but DEAD (no runner code, no anthropic lib, no API key). Earlier in this doc I called it a one-liner — that was wrong. |
| Tier 2 sample-row spot-check | **owed** | 5 family rulesets shipped without per-family review (accepted risk). If a real valuation looks off, send listing+number back and calibrate. |
| Task #15 — 14 pre-existing test failures | open | `fuelled_coverage`(5), `evidence`(4), `conversations`(4), `admin_pricing_tanks`(1). Fail in isolation — separate root cause from the event-loop fix (likely MockSession SQL-match gaps / assertion drift). Blocks a fully-green suite. |
| Task #3 — smoke-test *suite* design | open, scope-first | Curtis's original ask. Tonight's was a one-off live smoke, not the automated suite. Was paused on scope (pricing-only vs broad; cadence). |
| Task #2 — Mark's 10:27am screenshot | other agent | Gmail attachment + OAuth work delegated elsewhere. |
| Send rev notices + Gmail draft | Curtis | see Emails section. |

---

## How this session executed (style — match it)

- **Skills, rigidly:** `systematic-debugging` (root cause before any fix — found the event-loop and the deploy-strip this way), `test-driven-development` (every fix had a failing test first, RED→GREEN reported), `dispatching-parallel-agents` (independent fixes farmed to background agents on non-overlapping files), `verification-before-completion` (never claimed done without running the command and reading output).
- **Parallel agents for independent work, but verify their results yourself.** Agents were given strict file scopes ("touch only X, do NOT touch Y") to avoid collisions, and TDD criteria as the definition of done. Their summaries describe intent — always re-run the tests / re-read the diff. (Example: an agent's "no regressions" claim hid that its new `asyncio.run()` test worsened the event-loop pollution — caught by running the full suite.)
- **Evidence over assertion.** Langfuse traces proved the 60s timeout wall; `/proc` proved the Anthropic hang; baseline diff proved the 30 failures were pre-existing. Don't trust a hypothesis you haven't instrumented.
- **Memory notes for recurring lessons** (see below). Write them as you learn, not at the end.
- **Mark + Fuelled team are non-technical** — strip implementation detail from any outbound comms (`feedback_mark_non_technical_comms`). Curtis's email voice: short, direct, no em-dashes, no bullets, "Curt" sign-off.
- **Curtis owns technical calls** (arch/naming/sequencing); Mark owns what Fuelled users see. Don't frame technical decisions as needing Mark's nod.
- **Rev notice per user-visible change** (CLAUDE.md §5), one feature area per notice.

## Memory notes written this session (in the project memory dir)

- `feedback_deploy_from_main_only` — never `railway up` from a feature branch; deploy from `backend/` dir; spot-check after.
- `feedback_prefer_oauth_over_mcp` — Google Workspace via direct OAuth, not the shrunken MCP surface.
- `feedback_mark_non_technical_comms` — strip implementation detail from Mark/Fuelled comms.

(Plus pre-existing notes on Railway access, Curtis email voice, report styling, etc. — read `MEMORY.md`.)

---

## Fast restart checklist

1. `git -C /Users/lynch/Documents/projects/fuelled-nova-v2 log --oneline -5` — confirm HEAD is `f4c4d8d` (or later) and you're on `main`.
2. `curl -s -o /dev/null -w "%{http_code}" https://api.fuellednova.com/api/health` — expect 200.
3. Read `MEMORY.md` + this file.
4. If deploying: `cd backend && railway up --service backend --detach` from `main`, then verify in container.
5. If touching the runner/enrichment: re-read "The enrichment runner" section above.
