# Tier 2 Workbook Column Spec — Locked 2026-05-13

> Canonical reference: `backend/app/pricing_v2/tier2/column_spec.py`.
> Runtime contract: `tests/pricing_v2/tier2/test_column_spec.py::assert_row_satisfies_spec`.
> If anything in this document disagrees with the code, the code wins — update this doc.

## Background

Tier 1 priced a portfolio and surfaced confidence as a portfolio-level band. Mark's feedback in the 2026-05-13 sync was that portfolio bands hide the per-row reasoning he needs on a sales call — when a buyer pushes back on a single asset, he needs to point at *that row* and show: how was RCN sourced, which methodology path ran, what the five confidence factors scored, why the LOW/MID/HIGH targets fell where they did, and what made the engine flag a row for review.

Tier 2 brings the same transparency shape Tier 1 had at portfolio scope down to the row. Every family ruleset (dehydrator, heater, treater, knockout-fwko, knockout-gas, knockout-flare, knockout-ambiguous) must emit a row that conforms to this schema. The schema is frozen — adding or renaming columns mid-build breaks every downstream consumer.

This doc is the human-readable contract. `column_spec.py` is the machine contract. `test_column_spec.py::assert_row_satisfies_spec` is the runtime gate every family test funnels through.

## At a Glance

| Group | Columns | What it captures |
| --- | --- | --- |
| Identity | 7 | listing identity, family, source |
| Inputs | 3 | size, age, condition input |
| RCN | 4 | replacement-new range + source |
| Methodology | 6 | which path was taken |
| Factor Weights | 5 | confidence weighting constants |
| Confidence Breakdown | 7 | 5-factor scores + composite + class |
| Price Targets | 3 | LOW/MID/HIGH per row |
| Comparables | 2 | comp count + summary |
| Reasoning | 3 | trail + review flag + reason |
| Hold | 1 | publication gate |
| Provenance | 2 | sold-anchor accounting (forward-compatible) |

Total: 43 columns. Verify by `len(TIER2_COLUMNS)`.

## Column Reference

### Identity

Seven columns that anchor a row to its source listing and tell the reader which family ruleset processed it. `Family` is the new field — Tier 1 only had `Category`. Tier 2 splits each broad category into family variants (e.g. `knockout-fwko` vs `knockout-gas` vs `knockout-flare`) and routes to a dedicated ruleset per family.

- **Listing ID** (`str`) — source-system primary key for the listing row.
- **Record ID** (`str`) — Nova's internal stable record ID.
- **Listing Name** (`str`) — the supplier's listing title.
- **Category** (`str`) — coarse category (compressor, dehydrator, separator, etc.). Inherited from Tier 1.
- **Family** (`str`) — Tier 2 family-level classification. Must be one of `VALID_FAMILIES` (see `column_spec.py:100-108`): `dehydrator`, `heater`, `treater`, `knockout-fwko`, `knockout-gas`, `knockout-flare`, `knockout-ambiguous`. `knockout-ambiguous` means the disambiguator failed; the row gets reviewed by a human.
- **Supplier Company** (`str`) — who's selling.
- **URL** (`str`) — link back to the live listing.

### Inputs

Three columns that record the engine's interpretation of the listing, separated from outputs so a reviewer can see what assumptions drove the price.

- **Size / Basis** (`str`) — the scaling parameter extracted from the listing (e.g. `"5 MMSCFD"`, `"10 MMBTU/hr"`, `"500 bbl/d"`). Free-text by design — family rulesets pick their own scaling basis.
- **Age Assumed (yr)** (`int | float`) — age in years used for depreciation. Comes from listing year if present, else family fallback.
- **Condition Assumed** (`str`) — A/B/C/D/F tier used for the condition factor.

### RCN

Four columns for the replacement-cost-new range and where it came from. Ordering is enforced: `Low <= Mid <= High` (validator invariant #6, `test_column_spec.py:65-66`).

- **RCN New Low** (`int | float`) — low end of the replacement-new range.
- **RCN New Mid** (`int | float`) — center of the replacement-new range; the engine scales this for depreciation.
- **RCN New High** (`int | float`) — high end.
- **RCN Source** (`str`) — provenance tag: `gold_table` (family-specific RCN lookup table), `fallback` (size-scaled formula when the gold table didn't match), or `sold_anchor` (a recent sold record dominated the RCN signal).

### Methodology

Six columns that record *how* the price was computed — the path through the engine, the curves applied, and the three factors that multiplied into the combined adjustment. This is the section Mark points at when a buyer asks "why this number."

- **Methodology Path** (`str`) — structured signature like `"dehydrator/teg/BTU-scaled"` or `"knockout-gas/vertical/fwko-table"`. Format is `<family>/<variant>/<rcn-method>`. Family rulesets are responsible for producing this string.
- **Depreciation Curve** (`str`) — name of the age curve used (e.g. `"dehydrator"`, `"heater"`). Tier 2 generally uses family-dedicated curves rather than Tier 1's generic ones.
- **Factor Service** (`float`) — service-condition factor (sweet vs sour, hours, etc.).
- **Factor Age** (`float`) — age-curve output at `Age Assumed`.
- **Factor Condition** (`float`) — condition-tier multiplier.
- **Factor Combined** (`float`) — product of the three. This is the multiplier applied to `RCN New Mid` to land at FMV center.

### Factor Weights

Five columns holding the *constants* used by `rcn_engine/confidence.py` to weight the five confidence dimensions into a composite score. They are emitted per row purely for transparency — they are not tuned per row. The values come from `confidence.py:19-23` (`W_RCN_SOURCE`, `W_DATA_VOLUME`, `W_DATA_FRESHNESS`, `W_SPECIFICITY`, `W_VARIANCE`). They sum to 1.0 by invariant (validator #7, `test_column_spec.py:68-76`); a family ruleset emitting weights that don't sum to 1.0 is a bug.

- **Weight RCN Source** (`float`) — currently 0.25.
- **Weight Data Volume** (`float`) — currently 0.25.
- **Weight Freshness** (`float`) — currently 0.10.
- **Weight Specificity** (`float`) — currently 0.25.
- **Weight Variance** (`float`) — currently 0.15.

If weights ever shift, they shift centrally in `confidence.py` and every row in subsequent runs reflects the new values.

### Confidence Breakdown

Seven columns: five component scores (each in `[0.10, 1.00]` per `MIN_CONFIDENCE` / `MAX_CONFIDENCE` in `confidence.py:15-16`), the weighted composite, and a discrete class. All five component scores come from `rcn_engine.confidence.calculate_confidence()`.

- **Conf RCN Source** (`float`) — how good was the RCN signal (gold table > sold anchor > fallback).
- **Conf Data Volume** (`float`) — how many comparable observations supported the price.
- **Conf Freshness** (`float`) — recency of the supporting data.
- **Conf Specificity** (`float`) — how completely the listing specified the inputs (year, condition, hours, size).
- **Conf Variance** (`float`) — coefficient of variation across comparables (lower spread = higher score).
- **Conf Composite** (`float`) — weighted sum.
- **Conf Class** (`str`) — must be one of `VALID_CONF_CLASSES` (`column_spec.py:111`): `automated` if composite >= 0.75 (`AUTOMATED_CONFIDENCE_THRESHOLD`, `confidence.py:13`), `hitl_review` if composite >= 0.40 (`HITL_REVIEW_THRESHOLD`, `confidence.py:14`), else `manual`.

### Price Targets

Three columns that capture the negotiation triangle for one asset. Ordering is enforced: `LOW <= MID <= HIGH` (validator invariant #5, `test_column_spec.py:58-63`).

- **Price Target LOW** (`int | float`) — risk-adjusted floor; the walk-away. A buyer offer below this should be declined.
- **Price Target MID** (`int | float`) — FMV center; the headline FMV for the row.
- **Price Target HIGH** (`int | float`) — asking-anchor ceiling; the opening number on the listing.

### Comparables

Two columns describing what supporting comps, if any, the engine pulled. In Tier 2 standalone runs (before the marketplace-comp join lands), `Comparables Count` will be `0` and `Comparables Summary` will read something like `"no comps (standalone run)"`.

- **Comparables Count** (`int`) — number of matched comps.
- **Comparables Summary** (`str`) — one-line summary (median, range, sources). Empty-state string when zero comps.

### Reasoning

Three columns that give the row a human-readable narrative and a review pathway when the engine wants a person to look. `Review Flag` and `Review Reason` are coupled: invariant #8 (`test_column_spec.py:78-80`) says `Review Flag = True` must come with a non-empty `Review Reason`.

- **Reasoning Trail** (`str`) — multi-line factor-by-factor explanation. Not a one-line summary — each line covers one decision (RCN source, age factor, condition factor, combined, final FMV). Newline-separated.
- **Review Flag** (`bool`) — `True` if the engine wants a human to look before this row is trusted in a price file.
- **Review Reason** (`str`) — required-non-empty when `Review Flag = True`. Specific machine-readable-ish reason (e.g. `"family=knockout-ambiguous"`, `"variance_score < 0.3"`).

### Hold

One column. Distinct from `Review Flag`: a row can be reviewed and still publish; a held row never publishes regardless of review state.

- **Hold From Publication** (`bool`) — `True` when the row should NOT appear on the platform (broken listing, duplicate, supplier withdrew, etc.). This is a hard gate, not a quality flag.

### Provenance

Two columns that track whether the sold-records corpus contributed to this row's RCN. Invariant #9 (`test_column_spec.py:82-86`) couples them: `Sold Anchor Used = True` iff `Sold Anchor Count >= 1`; `False` iff `Count = 0`. Forward-compatible — these stay `False` / `0` in the Tier 2 standalone run until the sold-records ingestion pipeline lands in a separate plan. Family rulesets must still emit them.

- **Sold Anchor Used** (`bool`) — did a sold record influence this row's RCN.
- **Sold Anchor Count** (`int`) — how many sold records contributed.

## Validity Rules (Cross-Column Invariants)

The validator in `test_column_spec.py:20-86` enforces nine rules. A row that fails any one is rejected at family-test time, before any workbook is written.

1. **Column completeness and order** (`test_column_spec.py:24-28`) — every row's keys must equal `TIER2_COLUMNS` exactly, in order. No extras, no missing, no reordering.
2. **Type contract** (`test_column_spec.py:30-46`) — every value matches `COLUMN_TYPES`. `None` is allowed only on `str`-typed columns (interpreted as empty cell).
3. **Valid Family** (`test_column_spec.py:48-51`) — `Family` is in `VALID_FAMILIES`.
4. **Valid Conf Class** (`test_column_spec.py:53-56`) — `Conf Class` is in `VALID_CONF_CLASSES`.
5. **Price target ordering** (`test_column_spec.py:58-63`) — `Price Target LOW <= Price Target MID <= Price Target HIGH`.
6. **RCN ordering** (`test_column_spec.py:65-66`) — `RCN New Low <= RCN New Mid <= RCN New High`.
7. **Factor weights sum to 1.0** (`test_column_spec.py:68-76`) — within `1e-6`. These are constants from `confidence.py`; a drift here means the family ruleset emitted hand-typed values instead of importing the canonical ones.
8. **Review flag has a reason** (`test_column_spec.py:78-80`) — `Review Flag = True` requires non-empty `Review Reason`.
9. **Sold-anchor consistency** (`test_column_spec.py:82-86`) — `Sold Anchor Used` and `Sold Anchor Count` cannot disagree.

## Schema Evolution

The spec is append-only in spirit. To add a column:

1. Edit `TIER2_COLUMNS` in `column_spec.py` first. Append at the end of the appropriate group, or in a new group at the bottom.
2. Add the column's type to `COLUMN_TYPES`.
3. Update the validator in `test_column_spec.py` if a new cross-column rule applies.
4. Update this doc — adjust the group table, add the column to the right Column Reference section, and add the new invariant to Validity Rules.
5. Update every family ruleset to emit the new column. The contract test will fail loudly if any ruleset forgets.

Order matters: code first, doc second. Doc-only changes drift silently.

Removing a column is harder. Cross-check every downstream consumer (workbook writer, frontend renderer, report.py, any cached output files) before deletion, and stage the removal with a migration window.

## Out-of-Scope (Now)

These were considered and explicitly deferred:

- **Marketplace comp join columns** — wait for read access from Mark.
- **Sold-anchor populated values** — `Sold Anchor Used` and `Sold Anchor Count` stay `False` / `0` in Tier 2 until the sold-records ingestion plan lands. Columns exist now for forward compatibility.
- **Tier 3 columns** — image-based field capture, manual fallback flows.
- **Frontend / UI rendering** — Mark's call in the 2026-05-13 sync was to move the weighted-visibility view out of the UI and into a report. This spec defines the report payload; the renderer is a separate workstream.

## Source

This spec was locked in the 2026-05-13 Mark Le Dain x Curt sync. Granola meeting: `3cd3ab18-a007-4b9c-b2c5-26fd03ff971a`. Per-row transparency (methodology, confidence breakdown, L/M/H targets, reasoning, factor weights) was the new requirement — a step beyond Tier 1's portfolio bands.
