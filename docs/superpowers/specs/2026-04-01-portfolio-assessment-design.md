# Portfolio Assessment & Report Quality Upgrade — Design Spec
**Date:** April 1, 2026
**Status:** Approved
**Branch:** TBD (from main)

---

## Problem

1. **Report quality is weak.** Current generators produce mechanical valuations — correct numbers but no business intelligence. Example reports (SCR Ariel, ARC Pump, Ovintiv VRU, Harsh's PwC report) have deep market context, buyer profiles, risk narratives, cost breakdowns, and strategic guidance. The generators have none of that.

2. **Multi-asset workflow is mechanical.** Current batch pricing processes items independently with no portfolio-level reasoning. Real jobs need intake extraction (emails, mixed inputs), category-level analysis, and disposition strategy.

3. **WCSB bias.** Agent defaults to Western Canadian Sedimentary Basin market context for all equipment regardless of location. US equipment gets irrelevant Canadian market commentary.

4. **No report choice.** Reports generate automatically in one format. Users need to choose when and what type of report to produce.

---

## What We're Building

Six changes to the existing pricing agent — no new pages, no duplicated infrastructure.

### 1. Enhanced Agent Reasoning (Prompt Upgrade)

**Goal:** The agent produces richer, location-aware analysis that matches the quality of the example reports.

**Changes to system prompt (`prompts.py`):**

- **Richer structured output schema.** Add fields for the analysis sections that appear in example reports:

```json
{
  "valuation": {
    "fmv_low", "fmv_high", "rcn", "confidence", "currency",
    "list_price", "walkaway",
    "factors": [{"label", "value", "rationale"}]
  },
  "comparables": [{"title", "price", "currency", "year", "location", "source", "url", "notes"}],
  "risks": ["..."],
  "market_context": "Demand drivers, regulatory environment, buyer pool — location-specific",
  "equipment_context": "What makes this equipment type distinct — rarity, parts sourcing, preference shifts",
  "condition_assessment": "Component-level condition analysis beyond letter grade",
  "cost_considerations": "Transport, re-cert, overhaul, pre-commissioning — with dollar ranges",
  "scenario_analysis": "As-is vs post-overhaul, individual vs lot sale, liquidation vs orderly",
  "marketing_guidance": "How to position, what to lead with in listing, expected timeline",
  "missing_data_impact": "What we don't know and how it affects the number",
  "key_value_drivers": ["Numbered factors supporting the valuation"],
  "assumptions": ["Equipment-specific assumptions, not boilerplate"],
  "sources": ["Fuelled.com — listing #12345", "OEM correspondence", "etc."]
}
```

The agent fills what's relevant — not every field for every item. A straightforward comp with good data might skip `scenario_analysis`. A 17-year-old unused VRU needs all of it.

- **Location-aware market context.** Remove WCSB default. Instruct agent to match market commentary to equipment location:
  - Canadian equipment → WCSB, Montney, Duvernay, provincial regulations
  - US equipment → Permian, Eagle Ford, Marcellus, US gas pricing, state-level context
  - Cross-border → transport costs, re-certification, FX friction
  - When ambiguous, ask the user

- **Quality reference material.** Load excerpts from example reports as "here's what good looks like" reference sections, similar to how RCN tables and risk rules are loaded. The agent sees the standard.

- **Comparable analysis upgrade.** Instruct agent to:
  - Note ask vs. transaction value conversion (80-90%)
  - Flag when comps are from the same operator/location (strongest basis)
  - Distinguish individual retail comps from bulk/lot sale comps
  - Include listing URLs for every comparable

### 2. Portfolio Assessment Workflow

**Goal:** Multi-asset jobs get intelligent intake, per-item pricing, and portfolio-level synthesis.

**Three phases — flexible, skip what's not needed:**

**Phase 1 — Intake & Extraction** (chat interaction)
- User uploads input: spreadsheet, email text, links, photos, or a mix
- Agent extracts asset list, identifies categories, flags missing data
- Presents summary: "I found 143 items across 6 categories. 12 are missing year/condition. Proceed?"
- User confirms or provides corrections
- Skipped for single-item queries (straight to Phase 2)

**Phase 2 — Individual Pricing** (existing batch infrastructure)
- Each item priced through the tool loop (search_comparables, lookup_rcn, calculate_fmv, check_risks)
- Uses the upgraded prompt producing richer structured output
- Intelligence panel shows live results table (see Section 3)
- For single items, this is the entire flow

**Phase 3 — Portfolio Synthesis** (one additional Claude call)
- After all items are priced, agent reviews the full results set
- Produces portfolio-level analysis:
  - Executive summary (total FMV range, category breakdown, confidence distribution)
  - Category-level observations ("57 line heaters = 40% of value, thin market")
  - Data quality summary (what was missing across the portfolio)
  - Disposition strategy (individual vs. lot sale, phased timing)
  - Offer analysis if buyer offer was provided (like Harsh's PwC report Section 4)
- Only runs for multi-item jobs (10+ items, or user requests it)

**API changes:**
- `POST /api/price/batch` — add optional `portfolio_synthesis: bool` flag (default true for 10+ items)
- Portfolio synthesis result stored alongside batch results
- New field in batch response: `synthesis: { executive_summary, category_observations, disposition_strategy, ... }`

### 3. Intelligence Panel Upgrade

**Goal:** Multi-item jobs show a results table, not just the last item's valuation card.

**Current behavior:** Intelligence panel shows one valuation card, one comps table, one risk card — for the most recent query only.

**New behavior for batch/portfolio jobs:**

**Results Table View:**

| # | Equipment | FMV Range | Confidence | Comps | |
|---|-----------|-----------|------------|-------|----|
| 1 | Ariel JGK/4 800HP | $380K-$480K | HIGH | 12 | View |
| 2 | Zedi Pump Skid (Double) | $1.5K-$2.5K | MED | 3 | View |
| ... | | | | | |
| **Total** | **143 items** | **$258K-$312K** | | | |

- Every row is clickable — "View" opens that item's full breakdown in the panel (valuation card, comps, risks)
- Back button returns to the table
- Links on every comparable, every listing reference
- Progress indicator during batch processing ("Pricing item 47 of 143...")
- Summary row with portfolio totals

**For single items:** No change — shows valuation card, comps table, risk card as today.

### 4. Three Report Tiers

**Goal:** User chooses when and which report to export. Reports are opt-in, not automatic.

**UI:** Report export button in the intelligence panel footer. Dropdown with three options:

- **One-Pager** — 1 page. Valuation summary table, total, basis of value, confidential footer.
- **Valuation Support** — 5-6 pages. Harsh's PwC format (the template everyone liked).
- **Full Assessment** — 10-15+ pages. Deep analysis with market context, risk narratives, overhaul economics.

**Tier 1: One-Pager**
1. Cover header (FUELLED APPRAISALS | FMV Valuation Support | Client)
2. Valuation Summary table (category, units, FMV mid/unit, subtotal, total)
3. Basis of Value statement (one line: "Fair Market Value, As-Is/Where-Is, ...")
4. Confidential footer

**Tier 2: Valuation Support Document** (Harsh's PwC format)
1. Cover + Valuation Summary table
2. Equipment Identification (parameter table: equipment, manufacturers, configurations, location, condition, accessibility, cataloguing status, sale context)
3. Equipment Categories & Condition Detail (per-category narrative paragraphs)
4. Comparable Sales Evidence (comps table with source/listing IDs, year, location, sold price, notes + Key Comparable Observations bullets)
5. Offer Analysis & Key Valuation Factors (if buyer offer provided — numbered factors with bold headers)
6. Valuation Reconciliation (metrics table: FMV by category, gross ask, buyer offer, net, offer vs. FMV delta)
7. Key Value Drivers (numbered list)
8. Sources (bulleted: Fuelled.com listings, proprietary database, buyer spreadsheet, operator data)
9. Disclaimer footer on every page

**Tier 3: Full Detailed Assessment** (SCR Ariel / ARC Pump format)
All of Tier 2, plus:
- Market Context section (regulatory drivers, demand trends, buyer pool)
- Detailed Valuation Methodology (RCN approach + market comparison with convergence)
- Component-Level Condition Assessment
- Cost Considerations (transport, re-cert, overhaul, pre-commissioning with $ ranges)
- Scenario Analysis (as-is vs. post-overhaul, individual vs. lot, liquidation vs. orderly)
- Marketing Guidance (positioning, listing title recommendations, timeline)
- Missing Data Impact Analysis
- Key Assumptions (equipment-specific, not boilerplate)
- Appendix (source documentation references)
- Signature block

**Currency:** All templates use the currency from the structured data (CAD or USD). No hardcoded "CAD".

**Links:** Every comparable in the report includes the source and listing reference (e.g., "Fuelled #62549"). In the .docx, these are formatted as references — not clickable hyperlinks in a formal report, but clearly attributed.

### 5. Report Generator Upgrades

**Goal:** Three Python generators matching the three templates above.

**Files:**
- `report_onepager.py` — Tier 1 generator (~80 lines)
- `report_support.py` — Tier 2 generator (~200 lines), replaces current portfolio_report.py structure
- `report.py` — Tier 3 generator (upgrade existing, ~350 lines)

**Shared:**
- `report_common.py` — Shared helpers: `_price()` (currency-aware), `_shade()`, `_font()`, cover page builder, disclaimer text, Fuelled Appraisals header/footer

**Key upgrades from current generators:**
- Currency-aware `_price()` — uses currency from structured data, not hardcoded CAD
- Executive summary pulls from agent's `market_context` and `key_value_drivers`
- Condition section renders agent's `condition_assessment` narrative
- Comps table includes `notes` column and "Key Comparable Observations" bullets
- Offer analysis section (Tier 2+) — when buyer offer is provided
- Valuation reconciliation table (Tier 2+) — FMV vs. gross ask vs. offer
- Assumptions are equipment-specific from agent output, not boilerplate list
- Sources section with attribution

### 6. Links Everywhere

**Goal:** Every reference to a listing, comparable, or source is linked — in both UI and reports.

**Intelligence panel:**
- Comparables table rows are clickable (already implemented — `window.open(url)`)
- Results table "View" links drill into item detail
- Source attributions link to listings where available

**Reports (.docx):**
- Comparables include source + listing ID (e.g., "Fuelled #62549, Kudu 5.7L V8, Redwater AB")
- Sources section lists all data sources used
- Formal reports use reference style, not hyperlinks (professional standard)

**Chat messages:**
- Agent already returns URLs from search_comparables — ensure these render as clickable links in the chat panel

---

## What We're NOT Building

- No new pages. Everything happens in the existing Pricing Agent page.
- No new database tables. Results stored in existing batch_log.jsonl and pricing_log.jsonl.
- No streaming/SSE. Synchronous REST with progress polling for batch jobs.
- No email intake automation. User uploads manually (email intake is a future feature).
- No Alembic migrations. No schema changes needed.

---

## Success Criteria

1. **Report quality matches examples.** A Tier 2 report for a 143-item PwC job looks like Harsh's PDF — same sections, same depth, same professional formatting.
2. **Location-aware.** US equipment gets US market context, not WCSB. Currency matches location.
3. **Agent reasoning is visible.** Market context, risk narratives, buyer profiles appear in the intelligence panel and flow into reports — not generated by the template.
4. **Multi-item UX works.** User can upload a spreadsheet, see a live results table, drill into any item, and export the report they want.
5. **Links work.** Every comparable in UI and reports is traceable to a source.

---

## Reference Documents

- `example-reports/SCR_Ariel_JGP_Valuation_FV-2026-0311.docx` — Tier 3 reference (single asset, full detail)
- `example-reports/ARC_Fresh_Water_Pump_Valuation_FV-2026-0312.docx` — Tier 3 reference (multi-unit, full detail)
- `example-reports/Ovintiv_VRU_Valuation_FV-2026-0314.docx` — Tier 3 reference (condition nuance)
- `example-reports/Ovintiv_Wyoming_Pricing_Logic_INTERNAL.docx` — Internal pricing logic reference
- `example-reports/FMV_Valuation Report_PwC_Longrun (1).pdf` — Tier 2 reference (Harsh's PwC format)
- `example-reports/FW_ PwC Valuation Report - (143x) Zedi & Kudu Shacks (1).eml` — Workflow context

---

## Client Feedback (Incorporated)

- **Mark (Discovery NR):** "Valuations are heavily indexed to the WCSB. Not relevant for US equipment. Reports talk about WCSB demand and trends that shouldn't be there for US items." → Fixed by location-aware market context.
- **Harsh (Fuelled):** "We really liked the format, comparisons, the factors, and sources. Can we have this kind of template for our Nova?" → Tier 2 template modeled on his PwC report.
