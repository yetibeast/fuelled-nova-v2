# Nova v2 Bulk Pricing Run — All 3,187 Unpriced Listings

## Context

Mark Le Dain (Fuelled CRO, mark.ledain@fuelled.com) sent a CSV of 3,187 unpriced listings and asked if Nova can bulk-price them so clients can approve pricing and Fuelled can reach 100% priced inventory. Curt (Arcanos) proposed a phased approach with a confidence rubric, and Mark greenlit the full run.

This prompt executes the full 3,187-row run end-to-end in Claude Code, with the Nova repo and databases available locally.

Input CSV is at `inputs/All_unpriced_listings.csv`. Coverage is roughly: 1,316 Tier 1 (Nova core — compressors, pumps, separators, tanks, storage bullets), 348 Tier 2 (Nova adjacent — heaters, treaters, FWKOs, dehydrators, vessels, exchangers, refrigeration, coolers, air compressors), and 1,523 Tier 3 (long tail — valves, misc, metering, pump jacks, buildings, flare stacks, transformers, MCCs, large process units).

---

## Required reading before you start

Do not start pricing until you've read items 1, 6, and 7.

1. `/mnt/skills/user/fuelled-equipment-valuation/SKILL.md` — full valuation methodology. Workflow C (Portfolio Pricing) is the relevant workflow.
2. `references/comparable_query_templates.md` — SQL templates for Nova comp searches
3. `references/escalation_factors.md` — year-over-year escalation for RCN
4. `references/rcn_reference_tables.md` — RCN family lookup tables
5. `references/depreciation_curves.md` — PASC condition curves by equipment type
6. `Bulk_Pricing_Confidence_Rubric.docx` — defines HIGH/MEDIUM/LOW bands, input signals, and auto-flag triggers. This is the rubric Mark signed off on.
7. `Sample_Bulk_Pricing_30.xlsx` — the exact output format. Match it. Do not invent columns or reorder.

---

## Tier assignment

Apply this segmentation as the first step. Add a `Tier` column to the working dataset:

**Tier 1 — Nova Core:** Compressor Package, Pump, Separator, Tank, Storage Bullet
**Tier 2 — Nova Adjacent:** Line Heater, Treater, Free Water Knockout, Flare Knockout, Dehydrator, Pressure Vessel, Heat Exchanger, Air Compressor, Refrigeration Plant, Cooler, Heat Medium Package
**Tier 3 — Long Tail:** everything else

---

## Per-row pricing requirements

**Every single row must produce a Confidence level (HIGH / MEDIUM / LOW) and a list of comparables used.** These are not optional. A row with a suggested FMV but no comparables and no confidence is incomplete and must be flagged for manual review rather than published.

### Confidence assignment

Follow the rubric exactly:

- **HIGH** — 5+ Nova comparables for similar configuration AND description includes manufacturer, model, year, primary spec (HP / capacity / pressure), and at least a condition hint. FMV defensible to ±10%.
- **MEDIUM** — Either 1–4 comparables OR thin description, but not both. FMV defensible to ±20%.
- **LOW** — 0 comparables OR niche/specialty OR FMV > $1M OR description unusable. FMV defensible to ±35% or wider. Must be flagged for human review before any client sees the number.

### Comparables requirements

For every row, capture the comparables that back the pricing decision. Minimum data per comparable:

- Source marketplace (Fuelled, Kijiji, IronHub, EquipmentTrader, Machinio, etc.)
- Title / description (first 120 chars)
- Asking price and currency
- Year (if available)
- Location
- URL back to the original listing
- Scrape date (so staleness is visible)

Store comparables as a JSON array in the `Comparables (JSON)` output column. Also produce a human-readable `Comparables Summary` column with the count and a 1-line summary of the range and median.

If zero comparables are found:
1. Try broader category search before giving up.
2. Try manufacturer-only search.
3. Try specs-based search (HP band, capacity band, pressure class).
4. If still zero, set `Comparables Summary` to "No direct comparables; RCN-only methodology" and confidence is automatically capped at LOW.

RCN evidence (which reference family was used, which appraisal evidence rows, what escalation factor) goes in a separate `RCN Evidence` column. This is not comparables but is part of defending the number.

---

## Auto-flag triggers (from the rubric)

Add a `Review Flag` column. Populate with the first trigger hit; leave empty if none. Hard-hold rows (do not publish without human review) must be clearly marked.

| Trigger | Flag value | Hold? |
|---|---|---|
| Suggested FMV > $1,000,000 | `FMV_OVER_1M` | Yes |
| Confidence = LOW | `LOW_CONFIDENCE` | Yes |
| Description contains "robbed", "stripped", "damaged", "fire", "flooded" | `DAMAGE_KEYWORD` | Yes |
| 5+ identical units from same supplier | `LOT_OPPORTUNITY` | No — add lot pricing as extra row |
| Original Price exists and differs from suggested FMV by >50% | `STALE_ORIGINAL_PRICE` | No — flag only |
| Category outside the 58 known categories | `UNKNOWN_CATEGORY` | Yes |
| No comparables AND no RCN family match | `NO_PRICING_BASIS` | Yes |

---

## Output format

Single xlsx file at `outputs/Fuelled_Bulk_Pricing_Full_Run.xlsx`. Match the sample file I prepared column-for-column, extended for confidence + comparables.

**Sheet 1: `Priced Listings`** (one row per listing, 3,187 rows)

| Column | Type | Notes |
|---|---|---|
| Tier | text | Tier 1 / Tier 2 / Tier 3 |
| Listing ID | text | From source CSV |
| Record ID | int | From source CSV |
| Listing Name | text | From source CSV |
| Category | text | From source CSV |
| Supplier Company | text | From source CSV |
| Associated Company | text | From source CSV |
| RCN Low ($CAD) | currency | Replacement Cost New low |
| RCN High ($CAD) | currency | Replacement Cost New high |
| Market Comp Low ($CAD) | currency | Low of comparable asking range |
| Market Comp High ($CAD) | currency | High of comparable asking range |
| Market Comp Median ($CAD) | currency | Median of comps |
| Suggested FMV ($CAD) | currency | Single-point fair market value |
| Suggested List ($CAD) | currency | FMV × 1.12 (12% list premium) |
| Walk-Away Floor ($CAD) | currency | FMV × 0.90 |
| Confidence | text | HIGH / MEDIUM / LOW — required, never blank |
| Comparables Count | int | How many Nova comps used |
| Comparables Summary | text | 1-line human-readable summary |
| Comparables (JSON) | text | Full JSON array, one object per comp |
| RCN Evidence | text | Which RCN family / appraisal row / escalation factor |
| Key Rationale | text | 1–2 sentences citing comp count, RCN basis, condition flags |
| Review Flag | text | Empty or trigger name |
| Hold From Publication | bool | TRUE if hard-hold, else FALSE |
| URL | text | From source CSV |

Colour-code the Confidence column (green/amber/red) and the Tier column (matching the sample).

**Sheet 2: `Summary`** — aggregated stats by tier and confidence:
- Row count by tier
- Row count by confidence within each tier
- Total suggested FMV by tier
- Hold-from-publication count by tier
- List of review flag counts

**Sheet 3: `Holds for Review`** — filtered view of every row where `Hold From Publication = TRUE`, sorted by FMV descending. This is the reviewer's queue.

**Sheet 4: `Lot Sale Opportunities`** — filtered view of `LOT_OPPORTUNITY` rows grouped by supplier + category, with per-unit FMV and suggested lot price (60-75% of per-unit × qty).

**Sheet 5: `Methodology`** — copy of the confidence rubric text, list of data sources queried, date of run, Nova database version/row count at time of run.

No PDFs, no Word docs, no markdown. Mark wants the xlsx.

---

## Execution order

1. **Read** the required docs (SKILL, rubric, sample output). Don't skip.
2. **Load** the CSV and apply tier assignment. Write a brief pre-run summary to stdout: row counts by tier, row counts with/without description, row counts with Original Price.
3. **Pre-flight query** the Nova database: confirm connection, row count of `listings`, row count of `pricing_evidence_intake`, last scrape date per source. Fail loudly if any of these are wrong.
4. **Price Tier 1 first** (1,316 rows). Checkpoint the partial output to xlsx after every 100 rows so a crash doesn't lose progress.
5. **Price Tier 2** (348 rows). Same checkpointing.
6. **Price Tier 3** (1,523 rows). These are where no-comparables outcomes are most common. Do not invent pricing. If there's no basis, set `Hold From Publication = TRUE` and `Review Flag = NO_PRICING_BASIS`.
7. **Build Sheet 2–5** (summary, holds, lot opportunities, methodology).
8. **Write** the final xlsx to `outputs/Fuelled_Bulk_Pricing_Full_Run.xlsx`.
9. **Print a run summary** to stdout: total rows priced, confidence distribution, total FMV, hold-count by tier, top 10 highest-FMV rows, top 10 flagged rows.

---

## What not to do

- Do not make up comparables. If Nova has 0 comps, the row is LOW confidence and the Comparables Summary says so.
- Do not silently override Original Price. If the listing has an Original Price and your FMV differs by >50%, flag it for review.
- Do not price items flagged with damage keywords ("robbed", "stripped", "fire", "flooded") without human review. These are hard holds.
- Do not price the MAN MGT6000 turbine gensets, the CSV Midstream amine package, or the unused PSA adsorbers as single-number FMVs. These need formal Workflow A reports — price them with wide ranges and `Hold From Publication = TRUE`.
- Do not invent new output columns. Match the sample + the additions listed above.
- Do not deliver partial output as the final. If Tier 3 is stuck, ship what's done and explicitly list what's missing in the run summary.

---

## Legal and formatting constraints

- All FMV values are "Fuelled's opinion of fair market value," not certified appraisals. The xlsx must include this disclaimer in Sheet 5 (Methodology).
- Asking prices in comparables are 80–90% of transaction prices. FMV figures already account for this.
- All values in CAD. If a Nova comp is in USD, convert and note the FX rate used in the per-comp JSON.
- Legal entity name: Fuelled Energy Marketing Inc. (never "Fuelled Technologies").

---

## Success criteria

The run is successful when:

1. All 3,187 rows have a non-blank Confidence value.
2. All rows have either comparables data OR a clearly stated "no comps available" reason.
3. Every HIGH confidence row has 5+ comparables captured.
4. Every FMV over $1M has `Hold From Publication = TRUE`.
5. The output xlsx opens cleanly, has all five sheets, and visually matches the sample format.
6. The run summary printed to stdout lets a human eyeball whether anything looks off before Mark sees the file.
