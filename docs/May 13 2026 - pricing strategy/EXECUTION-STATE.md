# Tier 2 Pricing Pass — Execution State

> **Paused 2026-05-13 evening at Task 1.4 GATE.** Awaits Curt signoff on the locked column spec before Chunk 2 (dehydrator vertical slice) starts.

## Pointer map

| What | Where |
|---|---|
| Strategy doc (Mark-facing) | `docs/May 13 2026 - pricing strategy/Fuelled_Pricing_Strategy_2026-05-13.pdf` |
| Implementation plan (1,002 lines) | `docs/superpowers/plans/2026-05-13-tier2-pricing-pass.md` |
| Column spec — runtime contract | `backend/app/pricing_v2/tier2/column_spec.py` |
| Column spec — human-readable | `docs/superpowers/specs/2026-05-13-tier2-column-spec.md` |
| Spec contract test + validator | `tests/pricing_v2/tier2/test_column_spec.py` |
| HubSpot CRM corpus (gitignored) | `seeds/hubspot/all-records.csv` (204k rows × 30 cols) |
| Worktree for implementation | `/Users/lynch/Documents/worktrees/fuelled-nova-v2-tier2` |

## Branch state

**Main** has the locked plan + the gitignore for HubSpot exports:
```
8c90ea3  chore: gitignore seeds/hubspot/ — customer CRM exports
579078a  docs(tier2): implementation plan locked 2026-05-13
35e1512  feat: US O&G buyer deep-pass + competitor-inbox catch-all capture (#16)
```

**`feat/tier2-pricing-pass`** worktree has Chunks 0+1 committed (newest first):
```
cab9cbd  docs(tier2): human-readable column spec
433fd0e  test(tier2): add error message to Conf Class invariant 4
e116011  test(tier2): spec contract test + assert_row_satisfies_spec helper
a9da363  refactor(tier2/column_spec): apply code-review fixes
50ea681  feat(tier2): lock column spec module (43 cols, 7 family values)
d04c68c  feat(tier2): scaffold tier2 module
```

## Tasks complete (5 of 30)

- [x] **Task 0.1** Worktree created — `/Users/lynch/Documents/worktrees/fuelled-nova-v2-tier2` on `feat/tier2-pricing-pass`
- [x] **Task 0.2** Tier 2 module + tests package scaffolded
- [x] **Task 1.1** Column spec module locked — 43 cols, 7 family values, 3 conf classes, `Tier2Row` dataclass with strict `.to_dict()` (4 code-review fixes applied)
- [x] **Task 1.2** Spec contract test — `assert_row_satisfies_spec` validator (9 invariants) + 4 unit tests, all PASS, full suite preserved (was 13/366, now 13/370)
- [x] **Task 1.3** Human-readable spec doc — 1,943 words, all 43 cols named, 9 invariants quoted with line citations

## 🚪 Paused at Task 1.4 — Curt signoff GATE

Three open questions blocking Chunk 2:

1. **Column groups — 10 or 11?** Doc treats `Hold From Publication` as its own group; `column_spec.py` groups it inline with Reasoning. Doc-table-only tweak either way. Pure presentation question.
2. **Knockout naming convention.** Kebab-case for sub-families (`knockout-fwko`, `knockout-gas`, `knockout-flare`, `knockout-ambiguous`); flat for base families (`dehydrator`, `heater`, `treater`). Asymmetric on purpose — sub-families are variants of one parent concept. Mark will see these values in the workbook `Family` column.
3. **`to_dict()` strict mode.** Now raises `ValueError("Tier2Row missing required columns: [...]")` on missing keys (deviation from plan's byte-identical spec; code reviewer recommended for fail-loud semantics). OK?

## Environment

- Python 3.13.12 in worktree venv at `backend/.venv` (created via `uv`)
- pytest 9.0.3 + asyncio plugin
- `.env` copied from main (DATABASE_URL etc.); not tracked
- `conftest.py` at worktree root inserts worktree root onto `sys.path` so `from backend.app...` imports resolve

## Test baseline

13 pre-existing failures in `test_fuelled_coverage.py` — UNRELATED to Tier 2 work, confirmed via `git stash` baseline comparison. 4 new Tier 2 tests added; full suite is now `13 failed, 370 passed`.

## What's next when the gate clears

**Chunk 2 — Dehydrator vertical slice** (Tasks 2.1-2.6, ends at second GATE for sample row review):

- 2.1 Variant classification (TEG / mole sieve / generic)
- 2.2 RCN scaling by MMSCFD (RCN brackets are PLACEHOLDERS — must calibrate against `seeds/rcn_price_reference_seed_v2.xlsx` and/or `seeds/hubspot/all-records.csv` before 348-row run)
- 2.3 Dedicated depreciation curve
- 2.4 Service factor + reasoning-trail builder
- 2.5 End-to-end `price_dehydrator()` returning spec-compliant row
- 2.6 🚪 GATE — Curt review on real sample row

Then Chunks 3-6 fan out: knockouts (3-way disambiguation), heaters, treaters, batch runner, 348-row dry run.

## HubSpot corpus arrival (same day, afternoon)

Mark shared `hubspot-crm-exports-all-records-2026-05-13.zip` (2.0 MB → 9.2 MB extracted, **204,057 rows × 30 columns**). Now lives at `seeds/hubspot/` (gitignored). It's the full Fuelled listings backbone — active + closed deals — not only sold records.

**Sold-records subset** = rows where `Stage` is closed-won AND `Deal Close Date` populated. **Per anti-drift rules in the locked plan, sold-records ingestion stays OUT OF SCOPE for current Tier 2 work** — the column spec already carries forward-compatible `Sold Anchor Used` / `Sold Anchor Count` columns (stay `False`/`0` until ingestion is built in a separate plan).

But the corpus enables earlier RCN-bracket calibration: replaces "placeholder, confirm with Curt" notes in Chunks 2-5 with real Fuelled history. See `seeds/hubspot/README.md` for schema and how this lands.

## Execution mode

Subagent-driven-development per `superpowers:subagent-driven-development`. Each task: implementer subagent → spec compliance reviewer → code-quality reviewer → fix loop → commit. ~5 dispatches per task on average.

Discipline relaxations taken today (and why):
- Trivial mechanical steps (Tasks 0.1, 0.2): done directly without subagent dispatch — would have been pure overhead for `git worktree add` and creating two empty `__init__.py` files.
- 1-line fix on Task 1.2 (invariant 4 error message): reviewer explicitly said it didn't warrant re-review; applied via `Edit` directly.
- Task 1.3 doc review: skipped subagent reviewers since Task 1.4 IS Curt's review of the doc — back-to-back review would be wasteful.

To pick up: open the worktree, review the 3 spec files (link table above), answer the 3 open questions, signoff (or change requests), then dispatch the implementer for Task 2.1.
