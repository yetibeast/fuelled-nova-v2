---
name: fuelled-equipment-valuation
description: "Generate professional equipment valuation reports and pricing analysis for Fuelled Energy Marketing Inc. Use this skill whenever asked to price, value, appraise, reprice, review, or create a pricing report for oilfield or industrial equipment — including pumps, compressors, generators, separators, tanks, pump jacks, VRUs, heaters, dehydrators, or any rotating/static equipment. Triggers on: 'pricing report', 'fair market value', 'FMV', 'valuation', 'what is this worth', 'price this equipment', 'equipment appraisal', 'RCN', 'replacement cost', 'suggested price', 'reprice', 'lower price', 'review these estimates', 'bulk pricing'. Also triggers when forwarded emails from clients asking for equipment pricing, when PO/drawing packages are attached, when spreadsheets of equipment listings need pricing, or when reviewing someone else's valuation estimates. This skill covers four workflows: formal FMV reports, bulk repricing, portfolio pricing, and peer review."
---

# Fuelled Equipment Valuation Skill

## Overview

This skill produces professional equipment pricing deliverables for Fuelled Energy Marketing Inc. (fuelled.com). Deliverables range from formal Word document valuation reports to bulk pricing spreadsheets to internal review emails, depending on the request type.

**Legal entity name:** Fuelled Energy Marketing Inc. (never "Fuelled Technologies")
**CRO:** Mark Le Dain (mark.ledain@fuelled.com, 403-999-1057)
**Operations:** Harsh Kansara (harsh.kansara@fuelled.com, 403-390-3364)

## Four Workflows

### Workflow A: Formal FMV Report
**Trigger:** Client asks for fair market value on specific equipment with drawings/POs attached.
**Output:** Word document (.docx) that Fuelled sends directly to the client.
**Examples:** ARC Resources pump packages, Strathcona Ariel JGP compressor, Ovintiv VRU skid.
**See:** Step-by-step instructions in "Formal Report Workflow" below.

### Workflow B: Bulk Repricing
**Trigger:** Mark or Harsh asks for lower suggested prices with reasons for a large inventory.
**Output:** Spreadsheet (.xlsx) with suggested prices + bullet reasons per row, plus an internal logic document (.docx) explaining the strategy.
**Examples:** Ovintiv Wyoming 129 items, stale inventory repricing.
**Key signals:** "lower suggested prices", "bullets/reasons for why it should be lower", "any format works", large CSV or listing export attached.
**See:** "Bulk Repricing Workflow" below.

### Workflow C: Portfolio Pricing
**Trigger:** Mark needs value estimates for a client's full equipment inventory (often newly catalogued).
**Output:** Spreadsheet with columns for RCN approach, market comp approach, suggested FMV, confidence, and rationale per item.
**Examples:** Discovery Natural Resources 213 items.
**Key signals:** "suggested price and more detailed rationale", "valuation approaches", "average/suggested FMV", "notes on sources", large listing spreadsheet attached, items in Draft status.
**See:** "Portfolio Pricing Workflow" below.

### Workflow D: Peer Review
**Trigger:** Harsh or Mark asks for feedback on FMV estimates produced by someone else (often free Claude or another tool).
**Output:** Email reply with item-by-item feedback — what's solid, what's too high/low, what info is missing.
**Examples:** Gran Tierra FMV review.
**Key signals:** "what do you think?", "this is what Claude provided", spreadsheet with existing FMV estimates, request for review/feedback.
**See:** "Peer Review Workflow" below.

---

## Data Sources

### Fuelled Nova Database (Primary)
The Fuelled Nova PostgreSQL database contains ~25,000 equipment listings scraped from 16+ sources across the WCSB and North American markets. This is the primary source for market comparables.

**How to access:** Run SQL queries against the `listings` table. See `references/comparable_query_templates.md` for templates.

**Key fields:**
- `title` — Equipment description (searchable with ILIKE)
- `canonical_manufacturer` — Normalized manufacturer name
- `canonical_model` — Normalized model
- `category_normalized` — Consolidated equipment category (22 groups)
- `price` — Listed asking price (CAD or USD)
- `currency` — CAD or USD
- `source_name` — Which marketplace (Fuelled, Kijiji, IronHub, EquipmentTrader, Machinio, etc.)
- `location` — Geographic location
- `year` — Year of manufacture (when available)
- `hours` — Operating hours (when available)
- `condition` — Condition description (when available)
- `specs` — JSONB field with extracted specifications (horsepower, etc.)
- `url` — Link to original listing
- `scraped_at` — When the listing was captured

**Search strategy:**
1. Start with direct keyword match on title (manufacturer + equipment type)
2. Broaden to category if direct match is thin
3. Pull category stats (count, avg, min, max) to show search was comprehensive
4. Use specs JSONB for HP range filtering when keywords fail
5. Always note total database size and category count in reports

**Important:** Asking prices are NOT transaction prices. Actual transaction values are typically 80-90% of listed asking price. State this in reports.

### Appraisal Evidence Database
The `pricing_evidence_intake` table contains 780+ rows extracted from professional appraisal PDFs spanning 2020-2026. This provides appraiser-certified RCN values and FMV/RCN ratios.

**Key sources:** ATB Operating (2020), Abbey Resources (2021), Caliber (2022), CLEANTEK (2024), FutEra Solar Titan (2025), plus Fuelled's own reports.

**Important:** Historical RCN values must be escalated to current-year CAD before use. See `references/escalation_factors.md`.

### RCN Reference Tables
The `rcn_price_references` table and seed spreadsheet contain baseline replacement costs by valuation family, frame, stage count, and drive type. See `references/rcn_reference_tables.md`.

### Listing Performance Data
For Workflow B (bulk repricing), the Fuelled platform provides:
- **Date Created** — How long the item has been listed
- **Total Listing Views** — How many people have seen it
- **Status** — Draft / Active / Sold

**Time on market + views + no sale = the market saying the price is wrong.** This is often the strongest repricing argument, stronger than any comparable. An item with 5,000 views over 8 years and no sale is not undiscoverable — it is overpriced.

---

## Formal Report Workflow (Workflow A)

### Step 1: Extract Equipment Identity

Read all available source material — emails, POs, drawing packages, spec sheets, photos. Extract:

| Field | Description | Example |
|-------|-------------|---------|
| Equipment type | What it is | Centrifugal pump package |
| Manufacturer/Model | OEM identity | Pioneer SC10B2M17+M0 |
| Configuration | Package scope | Package w/ building, MCC, VFD |
| Drive type | Power source | Electric motor (WEG 700HP) |
| HP/Capacity | Primary sizing | 700 HP / 20,000 m³/day |
| Service | What it handles | Sweet fresh water |
| Year built | Age reference | 2019-2020 |
| Hours | Operating life consumed | 5,207 - 9,339 hrs |
| Condition | PASC rating if known | Assumed B (Good) |
| Quantity | How many units | 4 |
| Original cost | If available from POs | $550,000/unit all-in |
| Location | Where the equipment sits | Grande Prairie, AB |

**Critical extraction points from drawings:**
- P&ID: Every component (pumps, motors, VFDs, heaters, controls, instrumentation, tag numbers)
- GA drawings: Package dimensions, weight, building configuration
- Line designation tables: Pipe specs, design pressure, temperature range, materials
- Weight tables: Component-level weight breakdown
- Nozzle schedules: Connection sizes
- Title block: Packager, project number, revision dates (use for year estimation)

**Critical extraction from POs:**
- Line item costs (what the buyer actually paid)
- Revision history (scope changes, adders, credits)
- Supplier identity (who built it — important for OEM RCN)
- Date (for escalation calculations)

**Critical extraction from emails:**
- Client name and contact
- What they want (FMV for sale, insurance value, financing, etc.)
- Condition hints ("overhaul costs too high" = condition C, "unused" = condition A but check age)
- Hours and year if mentioned
- Urgency / timeline

### Step 2: Determine Replacement Cost New (RCN)

RCN = what it would cost to replace this equipment with a functionally equivalent new unit today, in CAD.

**Priority order for RCN sources:**

1. **OEM quote or correspondence** (highest confidence) — If the manufacturer provides current pricing or escalation factors. This is gold.
2. **Original PO cost + escalation** — Take the original all-in cost, apply escalation factor for years elapsed. See `references/escalation_factors.md`.
3. **Appraisal evidence** — Use RCN values from the pricing_evidence_intake table, escalated to current year.
4. **RCN reference table lookup** — Use the `rcn_price_references` table. Match by valuation family, frame/model, stages, drive type, configuration.
5. **HP-based scaling** — `base_price * (target_hp / base_hp) ^ scaling_exponent`. Default exponent = 0.6 for rotating equipment.
6. **Back-calculated from auction data** — Hammer price / (age_factor × condition_factor) = implied RCN. Least reliable.

**Component-level RCN is better than lump sum.** When possible, break the RCN into component groups to show what portion of the value comes from each major component. This is critical when market comps only exist for one component (e.g., bare pump) but not the full package.

Typical component splits for packaged equipment:

| Component Group | % of Package RCN |
|----------------|------------------|
| Prime mover (engine/motor) | 20-35% |
| Driven equipment (compressor/pump) | 15-25% |
| VFD / electrical drive | 5-15% |
| Building / enclosure | 10-20% |
| MCC / switchgear / controls | 10-20% |
| Piping, instrumentation, ancillary | 5-15% |

### Step 3: Query Market Comparables

Run comparable searches against the Fuelled Nova database. See `references/comparable_query_templates.md` for SQL templates.

**Search strategy:**
1. **Direct match** — Same equipment type + manufacturer + similar HP + same service
2. **Manufacturer match** — Same OEM, any model
3. **Driver match** — Same engine/motor model (e.g., CAT 3306 driven packages)
4. **Category stats** — Overall market depth for this equipment class
5. **HP range search** — Specs JSONB field for horsepower in target range

**Interpreting results:**
- Strong comps: Same manufacturer AND similar HP AND same service AND same region
- Moderate comps: Same type, different manufacturer or HP range
- Weak comps: Different equipment class but similar HP (use for context only)
- Thin comps: Normal for high-spec packages. State explicitly and rely on RCN.
- Asking prices ≠ transaction prices. Actual transactions are 80-90% of asking.

### Step 4: Apply Depreciation

Fair Market Value = RCN × age_factor × condition_factor × hours_factor × service_factor × premiums

See `references/depreciation_curves.md` for full tables. Summary:

**Age Retention (rotating equipment):**

| Age | Factor |
|-----|--------|
| 0-1 yr | 0.90 |
| 2-3 yr | 0.80 |
| 4-5 yr | 0.65 |
| 6-8 yr | 0.50 |
| 9-12 yr | 0.38 |
| 13-15 yr | 0.28 |
| 16-20 yr | 0.20 |
| 21-25 yr | 0.15 |
| 26-30 yr | 0.10 |
| 30+ yr | 0.08 |

**Condition (PASC):** A=1.00, B=0.75, C=0.50, D=0.20

**Hours (rotating):** <5K=1.10, 5K-15K=1.00, 15K-30K=0.85, 30K-50K=0.70, 50K+=0.55

**Common premiums/penalties:**
- VFD equipped: +5%
- Complete turnkey package (building + MCC + controls): +5%
- Sour/NACE service: +15-25%
- ABSA/CRN certified with data sheets: +10%
- No data sheets / no registration: -15%
- Remote location (NWT, northern BC): -15%
- Unused but aged (zero hours, >10 years old): Apply age factor BUT use condition 1.50× (not PASC A) — see "Age vs. Condition" in risk rules

### Step 5: Check Risk Rules

Before finalizing the valuation, check `references/risk_rules.md` for equipment-specific risk factors that affect buyer confidence and should be disclosed in the report. These include:
- Controls/PLC obsolescence
- Idle equipment degradation (elastomers, seals, lubricants)
- Overhaul economics (does repair cost exceed post-repair value?)
- Component-specific discontinuation notices
- Pre-commissioning cost estimates

### Step 6: Build the Report

Generate a Word document (.docx) using the docx skill. Read `/mnt/skills/public/docx/SKILL.md` for docx-js instructions.

**Report structure (keep consistent across all formal reports):**

1. **Cover Page** — Title, client name, contact, prepared by (Fuelled Energy Marketing Inc.), date, reference number (FV-YYYY-MMDD), confidentiality notice
2. **Executive Summary** — Headline FMV range per unit, total portfolio value, valuation basis, effective date. One summary table. Keep it to one page.
3. **Equipment Description** — Package overview, technical specifications table (every component from P&ID), individual unit details (serial/unit numbers, hours, PO reference)
4. **Valuation Methodology** — RCN derivation with source attribution, depreciation adjustment factor table with rationale for each multiplier, base FMV calculation formula
5. **Market Comparables** — Comparable listings table with source/notes, comparables analysis, component cost breakdown (RCN vs. market validation), conclusion
6. **Fair Market Value / Unit-by-Unit Valuation** — Per-unit FMV table (low/high/confidence), volume pricing consideration, recommended list pricing with walk-away floors, overhaul economics (if applicable)
7. **Key Assumptions and Limiting Conditions** — Numbered list (8-10 items typically)
8. **Market Context** — 3-5 bullets on current market conditions (only if adds value)
9. **Disclaimer** — Standard non-appraisal disclaimer
10. **Signature Block** — Fuelled Energy Marketing Inc., contact info
11. **Appendix** — PO references, drawing package summary, OEM correspondence (if applicable)

**Formatting standards (DO NOT CHANGE — clients like the current format):**
- US Letter (12240 × 15840 DXA), 1" margins
- Font: Arial throughout
- Headers: Dark navy (#1A1A2E) background, white text
- Accent: Blue (#0077B6) for subheadings
- Section dividers: Orange (#E85D04) horizontal rules
- Alternating row shading: #F5F5F5
- Currency format: $#,##0 CAD
- Header bar: "Fuelled Energy Marketing | Equipment Valuation Report | [Reference #]"
- Footer: "Confidential | fuelled.com"

### Step 7: Deliver

1. Generate the .docx file
2. Validate with the docx validation script
3. Preview key pages (convert to PDF → images)
4. Present the file to the user
5. Summarize key numbers and flag items needing validation

---

## Bulk Repricing Workflow (Workflow B)

**When:** Large inventory of stale or overpriced listings needs suggested lower prices with reasons.

### Inputs
- CSV or spreadsheet export from Fuelled platform (typically: Category, Title, URL, Location, Price, Date Created, Views, Account)
- Mark's direction on what he wants (usually: "lower prices with bullets for each")

### Process
1. **Categorize items** — Group by equipment category, count duplicates
2. **Identify pricing signals:**
   - Time on market (date created → days listed)
   - Views vs. sales (high views + no sale = overpriced)
   - Volume of identical items (57 identical line heaters = oversupply)
   - Location penalties (Wyoming = cross-border, remote = freight)
   - Missing data (no year/hours/condition = buyer discounts further)
3. **Set prices by category** — Use RCN tables and comps for high-value items, commodity pricing for small items
4. **Recommend lot sales** for categories with 10+ identical items
5. **Calculate portfolio totals** — Current vs. suggested, overall reduction %

### Output — Two Files
1. **Spreadsheet (.xlsx):**
   - Tab 1: All items with columns: #, Category, Title, Current Price, Suggested Price, Reduction %, Reasons (top 4 bullets), Views, Days Listed, Location
   - Tab 2: Summary by Category with totals
2. **Logic Document (.docx, internal use):**
   - Why prices need to come down (structured arguments)
   - High-value item recommendations table
   - Lot sale recommendations table
   - Summary metrics

### Key Repricing Arguments (reusable)
- **Time on market:** "Listed since [date] with [X] views and no sale. The market has seen this equipment and passed at this price."
- **Volume oversupply:** "Listing [N] identical items simultaneously destroys pricing power. Every buyer knows there are [N-1] more behind the one they're looking at."
- **Missing data:** "No year, hours, or condition data. Every missing data point is a reason for a buyer to discount."
- **Location penalty:** Cross-border transport, ASME→ABSA re-registration, thin secondary market.
- **Equipment type issues:** Integral compressors declining, obsolete frames, site-specific process equipment.

---

## Portfolio Pricing Workflow (Workflow C)

**When:** New client inventory needs value estimates for the first time. Items are typically in Draft status (not yet published).

### Output Format (Mark's preferred)
Spreadsheet with columns:
- Existing: listingId, category, title, url, location, status
- Added: RCN Approach ($), Market Comp Approach ($), Suggested FMV ($), Confidence, Key Rationale, Sources/Notes

### Process
1. Group items by category
2. For high-value categories (compressors, gensets, large separators, treaters): Pull comps from database AND use RCN tables — show both approaches
3. For commodity items (small pumps, valves, meters, tanks): Use category-average pricing — don't over-engineer
4. For bulk/batch items (pallets of valves, batches of instruments): Lot pricing
5. Adjust for geography (Texas/Permian USD pricing vs. Alberta CAD)

---

## Peer Review Workflow (Workflow D)

**When:** Reviewing FMV estimates produced by someone else (free Claude, another appraiser, Harsh's quick estimates).

### Process
1. Read the existing estimates
2. Cross-reference each against our RCN tables, appraisal evidence, and depreciation curves
3. For each item, assess: solid / too high / too low / needs more info
4. Pay special attention to:
   - FMV/RCN ratios that are too high (>0.50 for aged rotating equipment is suspicious)
   - Items where free Claude likely doesn't have domain context (e.g., specific compressor frames, packager reputation)
   - Missing driver identification on compressor packages (can swing value $50K+)
   - Multiple identical units where volume discount should apply
5. Flag the top 3-5 items where the estimate is most likely wrong

### Output
Email reply with:
- Overall assessment ("70% of estimates are in a defensible range")
- Item-by-item feedback (grouped by category)
- Summary of recommended changes: push UP, push DOWN, GET MORE INFO
- What additional data would improve the estimates

---

## Cross-Border Framework

### US Equipment (Wyoming, Texas, Permian)
- **Currency:** All US listings are USD. Convert to CAD for comparison. Note the FX rate used.
- **Transport:** Cross-border transport to AB/SK buyer adds $5K-$15K per load depending on size and permitting.
- **Re-registration:** ASME-registered pressure vessels may need ABSA (Alberta) or TSASK (Saskatchewan) re-registration. Budget $2K-$5K per vessel.
- **Market depth:** Wyoming is thin. Texas/Permian is stronger. Both are thinner than AB/SK for oilfield-specific equipment.
- **Buyer pool:** Most likely buyers are Canadian operators or brokers. US-only buyer pool is smaller for oilfield production equipment outside the Permian.

### International (Kuwait, Middle East, etc.)
- **Use with extreme caution.** Equipment costs vary dramatically by region.
- **Flag as low confidence** for AB market pricing.
- **FX + logistics + re-certification** make direct comparison unreliable.

---

## Lot Sale and Volume Strategy

### When to Recommend Lot Sales
- 10+ identical or near-identical items in the same inventory
- Individual item value < $3,000 (transport cost approaches equipment value)
- Items listed > 2 years with no sale at current per-unit pricing

### Lot Pricing Formula
- Lot price = per-unit suggested price × quantity × 0.60 to 0.75 (lot discount)
- Justify: "A single buyer taking all [N] units at [lot price] gets equipment at [$/unit]. That buyer either reuses them or resells individually at [higher price] each."
- Always show per-unit economics for the lot buyer

### Volume Discount for Identical Units
- 2-3 identical units at same location: 5% discount per unit
- 4-10 identical units: 10-15% discount per unit
- 10+ identical units: Lot sale pricing (see above)

---

## Decision Trees

### "Which workflow?"
```
Client email with drawings/POs asking for FMV?
├── YES → Workflow A (Formal Report)
└── NO
    ├── Large inventory spreadsheet needing lower prices?
    │   ├── Items already priced → Workflow B (Bulk Repricing)
    │   └── Items unpublished/Draft → Workflow C (Portfolio Pricing)
    └── Someone else's estimates to review?
        └── YES → Workflow D (Peer Review)
```

### "Which valuation approach?"
```
Has OEM provided current replacement cost?
├── YES → Use OEM RCN as primary (highest confidence)
└── NO
    ├── Have original POs with cost breakdown?
    │   ├── YES → PO cost + escalation factor
    │   └── NO
    │       ├── Appraisal evidence exists for this equipment type?
    │       │   ├── YES → Escalated appraisal RCN
    │       │   └── NO → RCN reference table lookup + HP scaling
    │       └── Always search for market comps to validate
    └── Either way, search for market comps to validate
```

### "How to handle thin comparables?"
```
Market comps found for exact configuration?
├── YES → Use as primary, RCN as validation
└── NO
    ├── Comps for components (bare pump, engine, etc.)?
    │   ├── YES → Component comp validates that portion of RCN
    │   │         RCN methodology is primary for full package
    │   │         Show component cost breakdown table
    │   └── NO → RCN-only methodology, note absence of comps
    └── State explicitly: "high-spec industrial equipment typically
        trades through direct negotiation, not open listings"
```

### "Electric vs. gas engine package?"
```
Drive type?
├── Gas engine → Higher package cost (engine is 20-35% of total)
│                Use engine_driver valuation family for driver component
│                Check gas engine comps separately
├── Electric motor → Lower base (no engine) BUT add VFD + MCC cost
│                    VFD can be 5-15% of package
│                    MCC/switchgear can be 10-20%
│                    Use recip_gas_elec_pkg or equivalent family
└── Integral → Different market entirely (Ajax/slow-speed)
               Use recip_gas_integral family
               Note: integral compressors declining in market preference
```

---

## Important Caveats

- **Never present FMV as a certified appraisal.** The disclaimer must state this is Fuelled's opinion, not a formal appraisal.
- **Always flag unverified assumptions.** If condition is assumed (not inspected), say so. If hours are reported (not verified), say so.
- **Recommend list pricing above FMV.** Typical 10-15% premium to allow negotiation room. Include walk-away floor (typically 90-92% of FMV low).
- **Volume discounts are real.** Multiple identical units as a lot = 5-10% discount is standard.
- **Transport is the buyer's problem.** Exclude from FMV. Note approximate cost per unit.
- **Currency matters.** All values in CAD unless stated. Note if USD conversion is relevant.
- **Report format is locked.** Clients like the current format. Do not change formatting standards.
- **Asking prices ≠ transaction prices.** Note the 80-90% conversion in reports when citing comps.
- **Time on market is evidence.** High views + no sale = the market saying the price is wrong.
