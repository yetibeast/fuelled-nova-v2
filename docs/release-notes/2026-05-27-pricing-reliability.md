# Nova rev notice — 2026-05-27 (pricing reliability)

**Subject: US deals now pull US comps + bigger batch reports complete reliably**

Audience: Fuelled team

This rev covers two fixes Mark hit directly today, plus one piece of internal hardening that unblocks autonomous seller-contact enrichment.

---

## What Mark asked for

> In that latest analysis on the EOG units a weird thing is that it keeps anchoring comps to Canadian priced items. May just be that it can't find scraped data in the US.
>
> — 2026-05-27

(And a separate batch report failure earlier in the day that completed only 20 of 113 items.)

## What we built

**1. Country filter on comparable search.** Nova's comp search now accepts a country argument and will scope to US or CA listings when set. The pricing agent picks this up automatically: if the equipment is located in a US state or the user mentions a US source / currency, Nova passes `country='US'` and only US-located comps come back. Same for CA. Without the argument, behavior is unchanged.

Country detection is tiered so it works across our mixed scraper sources: trusted `country` column first (Fuelled + IronHub), then trailing ISO codes in the location string (AllSurplus), then trailing state/province abbreviations (kijiji, EquipmentTrader, SurplusRecord), then full state/province names anywhere in the location text (BidSpotter, IronPlanet). Net effect: US deals stop drowning in Canadian volume even though most of our scrape pool is CA-sourced.

**2. Batch report per-item timeout doubled** from 60 to 120 seconds. Today's EOG report failed 93 of 113 items because each per-item Claude call hit a hard 60s wall while still working through the spec. Bumping to 120 absorbs the current call latency profile (rate-limit backoff + tool-loop iterations). Re-running the same EOG batch should now complete substantially more items.

**3. Recurring enrichment runner now has an explicit per-call timeout** so it can't hang indefinitely on a slow Anthropic response. Previously a single hung call could lock up the whole batch (we hit a 36-minute hang during today's first backfill attempt). Now it cleanly times out at 120s per seller and records the failure, letting the rest of the batch proceed.

## How to use it

1. **Country filter** — no workflow change. Price US equipment as usual; Nova handles the comp scoping itself. You'll see this reflected in the comparables table — US deals will show US-source rows (govdeals, allsurplus US, etc.) instead of Canadian auction houses dominating.
2. **Batch report** — no workflow change. Re-run any batch that previously timed out and expect more items to come back priced. The EOG report Mark uploaded today is a good first re-test.
3. **Enrichment runner** — internal, no user surface yet.

## What's NOT in this rev

- **Cron auto-enrichment still OFF.** The recurring pipeline can run safely now, but we haven't enabled the weekly schedule. Manual backfills only until you flip the cron on.
- **Seller mailout coverage hasn't expanded yet.** Mark's mailout CSV still shows ~24% of sellers with enriched leads (the same 11 from the May 10 workbook plus today's single smoke-test). The backfill against the remaining 175 sellers is the next thing to run now that the runner is hardened. Buyer CSV is already at 92% coverage and unchanged.
- **No PDF/spreadsheet export changes.** Same export format as before.

## What's next

- **Seller backfill** — re-attempt against the now-timeout-hardened runner. Target: bring seller mailout coverage from ~24% to ~100% at an estimated total cost of ~$12-15.
- **Enable weekly cron** for ongoing seller enrichment once the backfill validates.
- **Tier 2 sample-row spot-check** — the 5 family rulesets that shipped earlier tonight (heater, treater, knockouts, dehydrator, meter runs) didn't go through an explicit per-family sample review. If anything looks off in a real valuation, send the listing back and we'll calibrate.

Implementation notes: country detection logic in `backend/app/pricing_v2/tools.py`; batch timeout in `backend/app/api/batch.py`; runner timeout in `backend/app/pricing_v2/intel/providers/claude_parallel.py`. All on main.
