"""Report-specific prompt and message builder for Tier 2/3 Claude report pass."""
from __future__ import annotations

import json

# ── Few-shot examples (condensed from gold-standard reports) ─────────

_EXAMPLE_COMPRESSOR = """{
  "executive_summary": "Strathcona Resources Ltd. has requested a fair market valuation for one (1) surplus Ariel JGP 2-stage gas compressor package at Cactus Lake, SK. The unit is an Enerflex Model B145 with a CAT G3306NA engine (145 HP), approximately 18 years old and requiring overhaul. As-is FMV is $25,000-$40,000 CAD, supported by both RCN-D analysis and direct market comparables from the Fuelled database of 2,141 compressor listings.",
  "valuation_methodology": {
    "approach": "This valuation employs both RCN-D and Market Comparison approaches. Direct market comparables exist for 3306-driven 2-stage sweet gas packages, allowing cross-validation.",
    "rcn_derivation": {
      "narrative": "RCN estimated by scaling from known reference points for Ariel 2-stage packages in the 100-200 HP range. The JGP is the smallest 2-throw frame in the Ariel lineup, now uncommon in new builds.",
      "components": [
        {"component": "Ariel JGP frame + cylinders", "cost_range": "$55,000-$75,000"},
        {"component": "CAT G3306NA engine", "cost_range": "$55,000-$75,000"},
        {"component": "GEA Rainey coolers (inter/after + engine)", "cost_range": "$30,000-$40,000"},
        {"component": "BTB inlet scrubber + piping", "cost_range": "$20,000-$30,000"},
        {"component": "Skid, controls, instrumentation, packaging labor", "cost_range": "$65,000-$85,000"}
      ],
      "total_rcn": "$250,000-$300,000",
      "notes": "The JGP frame is uncommon in new builds — most packagers now start at JGJ/2 or JGC/2. This RCN represents a functionally equivalent new package."
    },
    "depreciation": {
      "formula": "$275,000 x 0.20 x 0.50 x 1.00 x 1.00 = $27,500",
      "factors": [
        {"factor": "Age Depreciation (18 yrs)", "multiplier": 0.20, "rationale": "Engine S/N prefix 07Y suggests ~2007 manufacture. Low end of 16-20 year band for rotating equipment."},
        {"factor": "Physical Condition", "multiplier": 0.50, "rationale": "Rated C (Fair). Owner states overhaul costs are prohibitive, indicating significant mechanical work required."},
        {"factor": "Operating Hours", "multiplier": 1.00, "rationale": "Hours not provided. Default baseline assumed (5,000-15,000 hr range)."},
        {"factor": "Service Condition", "multiplier": 1.00, "rationale": "Sweet gas service. No sour/NACE indicators on P&ID or piping specs."}
      ]
    }
  },
  "market_comparables": {
    "overview": "The Fuelled database contains 2,141 compressor listings, of which 554 have pricing data. Small-frame 3306-driven packages appear regularly on the secondary market.",
    "listings": [
      {"description": "CAT G3306NA / Gemini H302, 2-Stg Sweet", "price": "$50,000", "year": "1998", "location": "Vulcan, AB", "source": "Kijiji", "notes": "Best comp. Same engine, same stages."},
      {"description": "CAT G3306TA / GE FE332C, 2-Stg Sweet", "price": "$40,000", "year": "1988", "location": "Forestburg, AB", "source": "Kijiji", "notes": "Same engine class. Much older."},
      {"description": "CAT 3306 / Ariel JGA/2", "price": "$15,000", "year": "", "location": "", "source": "Fuelled", "notes": "Floor price. Likely distressed/field condition."},
      {"description": "CAT G3408TA / Ariel JGJ/2, 2-Stage", "price": "$145,000", "year": "", "location": "Nisku, AB", "source": "Fuelled", "notes": "Larger driver. Ceiling reference."}
    ],
    "analysis": "The two strongest comparables are the CAT G3306NA/Gemini at $50,000 (1998, Vulcan) and the G3306TA/GE at $40,000 (1988, Forestburg). Both are 3306-driven 2-stage sweet packages. The $15,000 Ariel JGA/2 sets the floor (distressed pricing). The $145,000 JGJ/2 with 3408 driver sets the ceiling. Market-indicated range: $25,000-$45,000 for a 3306-driven 2-stage sweet package in fair to good condition, aligning with the RCN-based FMV of $27,500."
  },
  "fair_market_value": {
    "scenarios": [
      {"scenario": "As-Is (Condition C, needs overhaul)", "fmv_low": 25000, "fmv_high": 40000, "confidence": "Medium-High"},
      {"scenario": "Post-Overhaul (Condition B)", "fmv_low": 45000, "fmv_high": 60000, "confidence": "Medium"},
      {"scenario": "Salvage / Parts (Condition D)", "fmv_low": 8000, "fmv_high": 15000, "confidence": "Medium"}
    ],
    "overhaul_economics": "A typical frame and valve overhaul for a JGP with cylinder re-bore runs $40,000-$60,000. Engine overhaul on a G3306NA adds $15,000-$25,000. Total overhaul: $55,000-$85,000. Post-overhaul FMV of $45,000-$60,000 does not justify overhaul at market rates. However, a buyer with in-house capability could achieve it for $30,000-$50,000, making an as-is purchase at $25,000-$35,000 economically attractive."
  },
  "assumptions": [
    "Physical condition assumed C (Fair) based on owner's statement that overhaul costs are prohibitive. Not independently inspected.",
    "Year of manufacture estimated at ~2007 based on engine S/N prefix 07Y. Not independently confirmed.",
    "Operating hours unknown. Valuation assumes normal hours for estimated age (5,000-15,000). If hours exceed 30,000, reduce FMV by ~15%.",
    "ABSA registration and data sheet availability not confirmed. Registered equipment commands a 10% premium.",
    "Transportation costs excluded. Typical SK-to-AB move: $8,000-$15,000.",
    "FMV assumes 90-180 day marketing period. Equipment requiring overhaul may take longer."
  ]
}"""

_EXAMPLE_VRU = """{
  "executive_summary": "Ovintiv Canada ULC has requested a sale price range for one (1) VaporTech rotary vane VRU package at 01-34-078-17 W6M near Farmington, BC. The unit is a Ro-Flo 7D rated at 243 DMSCFD with 40 HP electric drive, NACE MR0175 sour service rated, built in 2009 and unused (zero operating hours). FMV is $35,000-$55,000 CAD. The valuation reflects the tension between unused condition and 17 years of age — zero hours supports higher value, but age depreciation, elastomer degradation, and obsolete PLC controls (discontinued MicroLogix 1200) pull downward.",
  "valuation_methodology": {
    "rcn_derivation": {
      "components": [
        {"component": "Ro-Flo rotary vane compressor + motor", "cost_range": "$50,000-$70,000"},
        {"component": "Suction scrubber (CRN registered, NACE)", "cost_range": "$15,000-$25,000"},
        {"component": "Condensate + circulation pumps", "cost_range": "$8,000-$12,000"},
        {"component": "Coolers (after cooler + JW cooler)", "cost_range": "$15,000-$25,000"},
        {"component": "Shelter, heater, exhaust fans, structural", "cost_range": "$20,000-$30,000"},
        {"component": "PLC controls, instrumentation, wiring", "cost_range": "$25,000-$35,000"},
        {"component": "Piping, valves, fittings (NACE rated)", "cost_range": "$20,000-$30,000"},
        {"component": "Skid fabrication, assembly, testing, QC", "cost_range": "$30,000-$40,000"}
      ],
      "total_rcn": "$200,000-$280,000"
    },
    "depreciation": {
      "formula": "$240,000 x 0.20 x 1.50 x 1.15 x 1.10 x 0.90 = $43,600",
      "factors": [
        {"factor": "Age Depreciation (17 yrs)", "multiplier": 0.20, "rationale": "Standard 16-20 year band. Applied despite zero hours because age affects all components."},
        {"factor": "Condition (Unused/Zero Hours)", "multiplier": 1.50, "rationale": "Unused premium partially offsets age depreciation. A 17-year-old unused unit is worth significantly more than one with 50,000+ hours."},
        {"factor": "Service Rating (NACE/Sour)", "multiplier": 1.15, "rationale": "NACE MR0175 sour service metallurgy. Premium in Montney/Duvernay where H2S is common."},
        {"factor": "CRN Registration", "multiplier": 1.10, "rationale": "Active CRN for AB/BC use. Avoids $3K-$5K re-registration cost."},
        {"factor": "Controls Obsolescence", "multiplier": 0.90, "rationale": "MicroLogix 1200 / PanelView 300 discontinued by Allen-Bradley in 2017. Buyer may need $8K-$15K controls upgrade."}
      ]
    }
  },
  "assumptions": [
    "Zero operating hours confirmed by Ovintiv. Not independently verified through inspection.",
    "Elastomers, seals, lubricants, and electrical insulation condition after 17 years of idle outdoor installation not assessed. Pre-commissioning inspection strongly recommended ($3K-$8K).",
    "CRN registration assumed current. Ovintiv should confirm registrations have not lapsed.",
    "PLC controls (Allen-Bradley MicroLogix 1200 / PanelView 300) are discontinued. Upgrade cost estimated at $8,000-$15,000 if required.",
    "Transportation excluded. Unit weighs ~10,000 lbs, standard load. Typical Montney-area move: $3,000-$6,000.",
    "FMV assumes 60-90 day marketing period. VRU demand currently strong due to federal methane reduction targets (75% reduction from 2012 levels by 2030)."
  ]
}"""


def build_report_prompt() -> str:
    """System prompt for the report-generation Claude pass."""
    return f"""You are a senior industrial equipment appraiser writing a client-deliverable valuation report for a Western Canadian energy equipment dealer. Write with the authority and specificity of someone who has valued thousands of oilfield packages.

CRITICAL INSTRUCTIONS:

1. BE EQUIPMENT-SPECIFIC, NOT GENERIC.
   BAD: "Compressors depreciate over time."
   GOOD: "The Ariel JGP frame is uncommon in new builds — most packagers now start at JGJ/2 or JGC/2 for new compression at this HP range."

2. NAME YOUR SOURCES.
   BAD: "Based on market data."
   GOOD: "RCN derived from CSM Pump Packaging quote (Nathan Hutzul, March 2026)" or "Fuelled database of 36,000+ equipment listings across 16 sources."

3. SHOW THE MATH.
   Write the full depreciation formula with dollar amounts:
   "$275,000 x 0.20 x 0.50 x 1.00 x 1.00 = $27,500"

4. EXPLAIN EACH DEPRECIATION FACTOR with equipment-specific rationale.
   BAD: "Age: 0.20"
   GOOD: "Age Depreciation (17 years): 0.20 — Standard 16-20 year band for rotating equipment. Applied despite zero hours because age affects elastomers, seals, and electrical insulation."

5. ANALYZE COMPARABLES, DON'T JUST LIST THEM.
   BAD: "Several comparable listings were found."
   GOOD: "The $50K CAT G3306NA/Gemini is the strongest comp — same engine class, same stages, sweet service. The $145K Ariel JGJ/2 with 3408 driver sets the ceiling for small-frame Ariel packages."

6. EQUIPMENT-SPECIFIC ASSUMPTIONS.
   BAD: "Condition assumed good."
   GOOD: "ABSA registration status has not been confirmed. Registered equipment commands a 10% premium; equipment without documentation may require re-certification at $5,000-$8,000."

7. INCLUDE COST CONSIDERATIONS with dollar ranges.
   Transport, re-certification, overhaul estimates: "Typical frame overhaul for a JGP runs $40,000-$60,000. Engine overhaul on a G3306NA adds $15,000-$25,000."

8. USE PASC-STYLE CONDITION GRADING.
   A = Like-new / Unused, B = Good (operational, normal wear), C = Fair (needs work), D = Poor (parts/salvage).

9. FOR THE RCN BREAKDOWN, decompose into major components with individual cost ranges.
   Show the build-up: frame, engine/motor, coolers, scrubber, controls, skid/packaging.

10. MARKET CONTEXT must be location-specific.
    Reference WCSB conditions, Montney/Duvernay activity, regulatory drivers, buyer pool.

RESPONSE FORMAT: Return valid JSON matching this schema exactly:

{{
  "executive_summary": "2-3 paragraphs: who requested, what equipment, key findings, FMV range",
  "equipment_description": {{
    "overview": "paragraph describing the equipment in operational context",
    "specs_table": [{{"component": "str", "specification": "str"}}],
    "notes": "optional unit details or condition notes"
  }},
  "valuation_methodology": {{
    "approach": "paragraph explaining RCN-D methodology choice",
    "rcn_derivation": {{
      "narrative": "how RCN was determined (OEM quote, scaling, database)",
      "components": [{{"component": "str", "cost_range": "str"}}],
      "total_rcn": "str",
      "notes": "escalation factors, source references"
    }},
    "depreciation": {{
      "formula": "str showing full calc e.g. $275,000 x 0.20 x 0.50 = $27,500",
      "factors": [{{"factor": "str", "multiplier": 0.0, "rationale": "str"}}],
      "notes": "special considerations"
    }}
  }},
  "market_comparables": {{
    "overview": "paragraph on data availability and relevance",
    "listings": [{{"description": "str", "price": "str", "year": "str", "location": "str", "source": "str", "notes": "str"}}],
    "analysis": "2-3 paragraphs analyzing what the comps tell us"
  }},
  "fair_market_value": {{
    "summary": "paragraph with FMV range and confidence",
    "scenarios": [{{"scenario": "str", "fmv_low": 0, "fmv_high": 0, "confidence": "str"}}],
    "list_pricing": {{"fmv_midpoint": 0, "list_premium": "str", "recommended_list": 0, "walkaway_floor": 0}},
    "overhaul_economics": "paragraph if applicable"
  }},
  "market_context": ["location-specific bullet 1", "bullet 2"],
  "assumptions": ["equipment-specific assumption 1", "assumption 2"],
  "sources": ["source with specifics", "source 2"]
}}

EXAMPLES OF EXCELLENT OUTPUT:

Example 1 — Gas Compressor (Ariel JGP, 2-stage, CAT G3306NA driver):
{_EXAMPLE_COMPRESSOR}

Example 2 — Vapor Recovery Unit (Ro-Flo 7D, unused, NACE sour rated):
{_EXAMPLE_VRU}

Return ONLY the JSON object. No markdown fences, no commentary outside the JSON."""


# ── Multi-item (Tier 2 portfolio) prompt ────────────────────────────

_EXAMPLE_MULTI = """{
  "executive_summary": "PwC, in its capacity as receiver for Longrun Exploration, has requested a fair market valuation of 143 surplus Zedi and Kudu hydraulic pump jack packages located across approximately 74 well sites in the Redwater, Alberta area. The inventory comprises a mix of gas-driven and electric-driven units in double, triple, quadruple, and suitcase configurations, manufactured between 2011 and 2013. Approximately 60-70% of units are described as complete and recently shut down; 30-40% are flagged for possible parts missing or sabotage. Roughly 40-50% of locations are currently snowed in. Total assessed FMV Mid is $258,000 CAD on an as-is/where-is, orderly bulk-liquidation basis. The buyer's unconditional offer of $300,000 exceeds this by $42,000 (+16.3%), which the analysis below supports as reasonable.",
  "equipment_identification": {
    "manufacturers": "Zedi, Kudu Industries",
    "driver_types": "Gas Driven (GM 5.7L V8, Natural Gas, 1800 RPM) and Electric Driven",
    "configurations": "Double, Triple, Quadruple, and Suitcase (Single) packages",
    "year_range": "~2011-2013",
    "application": "Hydraulic pump jacks for oil well production",
    "location": "~74 well sites, Redwater, Alberta area (Townships 056-058, Ranges 20-23 W4M)",
    "condition_rollup": "Mixed: ~60-70% complete/recently shut down; ~30-40% flagged possible parts missing or sabotage",
    "accessibility": "~50-60% accessible; ~40-50% snowed in (seasonal)",
    "cataloguing_status": "NOT individually catalogued, inspected, or serial-number verified",
    "sale_context": "Receivership estate (PwC). Unconditional bulk offer, as-is/where-is"
  },
  "category_details": [
    {
      "name": "Gas Driven Zedi Hydraulic Pump Skid (Double) - 55 units",
      "narrative": "Spread across 27 locations in the Redwater area. Approximately 43 units are described as complete and recently shut down. Approximately 12 units are flagged as having possible parts missing or sabotage. Eight locations are currently snowed in and inaccessible. All gas driven units are equipped with GM 5.7L V8 natural gas engines rated at 1,800 RPM. This is the largest category and has the highest proportion of complete units."
    },
    {
      "name": "Electric Driven Zedi Hydraulic Pump Skid (Double/Quadruple) - 35 units",
      "narrative": "Spread across 20 locations. Approximately 20 units are complete/recently shut down; approximately 15 are flagged for possible parts missing or sabotage. Roughly 55% of locations are snowed in. Includes a mix of double and quadruple configurations. Electric drive units are valued comparably to gas equivalents in this market segment."
    }
  ],
  "comparables": {
    "approach": "The primary valuation approach is the Sales Comparison (Market) Approach, supported by three directly comparable sold transactions from the Fuelled.com marketplace. These comps are from the identical equipment population - same producer, same Redwater locations, same Zedi and Kudu brands - and were sold within the relevant market period.",
    "comps": [
      {"source": "Fuelled #62549", "equipment": "Kudu Industries 5.7L V8 Hydraulic Pump Skid", "year": "2011", "location": "07-21-057-22W4, Redwater AB", "sold_price": "~$2,000", "notes": "Fuelled Certified. GM 5.7L V8 NG engine, 1800 RPM. Connected to piping. S/N: H27G016"},
      {"source": "Fuelled #62451", "equipment": "Zedi 5.7L V8 Hydraulic Pump Skid", "year": "2012", "location": "07-21-057-22W4, Redwater AB", "sold_price": "~$2,000", "notes": "Fuelled Certified. GM 5.7L V8 NG engine. Not connected to piping. S/N: SJTP57GQ0023"},
      {"source": "Fuelled #63748", "equipment": "Zedi 50 HP Suitcase Pump Skid", "year": "N/A", "location": "11-22-056-21W4, Redwater AB", "sold_price": "~$1,000", "notes": "Fuelled Certified. Suitcase package. Connected to piping, welded to piles."}
    ],
    "key_observations": [
      "All three comps are from the same Redwater inventory and the same operator as the 143 subject units. This eliminates geographic, market-timing, and equipment-type adjustment requirements - the strongest possible comparable basis.",
      "The sold comps were Fuelled Certified: individually catalogued with detailed photo packages (33-38 photos each), serial number verification, condition inspection reports, and certified status information. The 143 subject units have NOT undergone this process.",
      "Full-size skid-mounted packages (Kudu #62549, Zedi #62451) sold at approximately $2,000 per unit. The suitcase package (Zedi #63748) sold at approximately $1,000 per unit, reflecting the smaller form factor and lower horsepower.",
      "All comps were sold as individual units to individual buyers through a public marketplace with marketing exposure. The subject 143 units are being sold in bulk to a single buyer without individual marketing - a fundamentally different sale dynamic."
    ]
  },
  "valuation_factors": {
    "narrative": "The buyer's unconditional offer of $300,000 CAD for all 143 units equates to approximately $2,098 per unit (blended). Our assessed FMV Mid totals $258,000 ($1,804/unit blended average). The offer exceeds our FMV assessment by $42,000 (+16.3%). The following factors support the reasonableness and favorability of the offer:",
    "factors": [
      {"name": "Sold Comparable Transactions", "rationale": "Three directly comparable units from the same inventory sold on Fuelled.com at approximately $2,000/unit (full-size) and $1,000/unit (suitcase). These were individually catalogued, Fuelled Certified, and sold as single units to individual buyers. The buyer's blended offer price of $2,098/unit exceeds the individual certified retail benchmark, which is favorable to the seller given the uncatalogued bulk nature of this transaction."},
      {"name": "Unconditional, As-Is/Where-Is Terms", "rationale": "The buyer is purchasing all 143 units unconditionally with no representations or warranties. The buyer assumes full responsibility for dismantlement, transportation, environmental compliance, and remediation costs at each of the ~74 well sites. This is a significant risk transfer and eliminates ongoing carrying costs for the estate."},
      {"name": "Uncatalogued Inventory Risk", "rationale": "The subject units have not been individually inspected, catalogued, or serial-number verified. The sold comps were Fuelled Certified with comprehensive inspection reports and 33-38 photo packages per unit. Without individual cataloguing, the true condition of each unit is unknown, warranting a material discount from certified retail values."},
      {"name": "Condition Uncertainty - Missing Parts & Possible Sabotage", "rationale": "Approximately 30-40% of all units are flagged by the operator as having 'possible parts missing or sabotage.' Without physical inspection, some units may be incomplete, non-functional, or require substantial refurbishment. This uncertainty significantly depresses achievable bulk value."},
      {"name": "Access Constraints - Snowed-In Locations", "rationale": "Approximately 40-50% of unit locations are currently snowed in and inaccessible for inspection or removal. This adds time, cost, and further condition uncertainty for the buyer."},
      {"name": "Volume & Bulk Sale Dynamics", "rationale": "Bulk purchases of 100+ identical units in the oilfield secondary market typically warrant a 15-30% discount from individual retail values. At $2,098/unit blended, the offer effectively applies zero volume discount relative to the proven comp benchmark - the buyer is paying above individual retail on a per-unit average despite taking the full bulk risk."}
    ]
  },
  "assumptions": [
    "Unit counts and category breakdown derived from operator's inventory list. Not independently verified through site inspection.",
    "Condition descriptions ('complete', 'parts missing', 'possible sabotage') reflect operator self-reporting. Not verified by physical inspection.",
    "Snowed-in / accessibility status is seasonal and current as of valuation date.",
    "FMV assumes orderly bulk liquidation to a single buyer over a 60-90 day marketing period.",
    "Transportation, dismantlement, and environmental remediation costs at each well site are buyer responsibility.",
    "Sold comparables are from the Fuelled.com marketplace, individually catalogued and Fuelled Certified."
  ],
  "sources": [
    "Fuelled marketplace sold transactions (Listings #62549, #62451, #63748)",
    "Operator inventory list (143 units across ~74 well sites, Redwater AB)",
    "Fuelled internal database of bulk wellsite equipment dispositions"
  ]
}"""


def build_multi_report_prompt() -> str:
    """System prompt for the Tier 2 multi-item (portfolio) report pass."""
    return f"""You are a senior industrial equipment appraiser writing a multi-item bulk valuation support document for a Western Canadian energy equipment dealer. The deliverable is a Tier 2 Support Document covering a portfolio or bulk inventory of equipment - the canonical example is a receivership estate selling 100+ similar units to a single bulk buyer.

CRITICAL INSTRUCTIONS:

1. WRITE FOR A BULK / PORTFOLIO CONTEXT, NOT INDIVIDUAL ITEMS.
   The buyer is acquiring a basket. Discuss the inventory as a population: condition rollup, location spread, accessibility, completeness rate, sale dynamics.

2. GROUP BY CATEGORY, NOT BY ITEM.
   Equipment is grouped by Category (e.g., "Gas Driven Zedi Hydraulic Pump Skid (Double)"). One narrative paragraph per category covering: unit count, location spread, condition spread, accessibility, equipment-specific notes.

3. PICK 3-5 REPRESENTATIVE COMPS, DON'T DUMP EVERY COMP.
   The strongest comps are sold transactions of identical equipment from the same operator/location. Show the math from the comp benchmark to the bulk per-unit price.

4. ANALYZE BULK-SALE DYNAMICS.
   Bulk buyers take risk that individual buyers don't: uncatalogued inventory, condition uncertainty, dismantlement, transportation, environmental, access constraints. These typically warrant 15-30% discount from individual retail values.

5. NAME SOURCES.
   "Three directly comparable Fuelled.com sold transactions" not "market data."

6. EQUIPMENT-SPECIFIC LANGUAGE.
   GM 5.7L V8 NG engines at 1800 RPM. CAT G3306NA. Ariel JGP. NACE MR0175. Use the actual makes/models in the data.

RESPONSE FORMAT: Return valid JSON matching this schema exactly:

{{
  "executive_summary": "2-3 paragraphs: who requested, total units, equipment type, location, condition rollup, total FMV, buyer offer if known",
  "equipment_identification": {{
    "manufacturers": "comma-separated list",
    "driver_types": "str",
    "configurations": "str",
    "year_range": "str",
    "application": "str",
    "location": "str",
    "condition_rollup": "str (e.g. '~60-70% complete; ~30-40% flagged...')",
    "accessibility": "str if relevant else empty",
    "cataloguing_status": "str (catalogued vs uncatalogued)",
    "sale_context": "str (e.g. 'Receivership estate. Unconditional bulk offer, as-is/where-is')"
  }},
  "category_details": [
    {{"name": "Category description - N units", "narrative": "paragraph on this category's spread, condition, equipment-specific notes"}}
  ],
  "comparables": {{
    "approach": "paragraph on valuation approach + why these comps are appropriate",
    "comps": [{{"source": "str", "equipment": "str", "year": "str", "location": "str", "sold_price": "str", "notes": "str"}}],
    "key_observations": ["bullet 1 (comp relevance)", "bullet 2 (cataloguing/certification gap)", "bullet 3 (per-unit price benchmarks)", "bullet 4 (bulk vs individual sale dynamics)"]
  }},
  "valuation_factors": {{
    "narrative": "paragraph framing the FMV vs offer (if offer known) or general bulk-dynamics framing",
    "factors": [{{"name": "Factor name", "rationale": "why this factor matters and how it affects bulk value"}}]
  }},
  "assumptions": ["6+ portfolio-level assumptions"],
  "sources": ["sources with specifics"]
}}

EXAMPLE OF EXCELLENT OUTPUT (PwC / Longrun receivership, 143 hydraulic pump-jack packages):

{_EXAMPLE_MULTI}

Return ONLY the JSON object. No markdown fences, no commentary outside the JSON."""


def build_multi_report_messages(
    results: list[dict],
    summary: dict,
    client: str,
    buyer_offer: float | None = None,
) -> list[dict]:
    """Build user messages for the multi-item report pass.

    Pre-groups results by category so Claude sees the portfolio shape, not 143 raw rows.
    """
    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        v = r.get("structured", {}).get("valuation", {})
        cat = v.get("category") or r.get("title", "Uncategorized")
        by_cat.setdefault(cat, []).append(r)

    # Compact per-category summaries for the prompt (don't dump every item)
    cat_summaries = []
    for cat, items in by_cat.items():
        fmv_lows = [it.get("structured", {}).get("valuation", {}).get("fmv_low", 0) or 0 for it in items]
        fmv_highs = [it.get("structured", {}).get("valuation", {}).get("fmv_high", 0) or 0 for it in items]
        sample_titles = [it.get("title", "")[:80] for it in items[:5]]
        # Pull a few comps from the first item in this category as representative
        sample_comps = []
        for it in items[:3]:
            comps = it.get("structured", {}).get("comparables", []) or []
            for c in comps[:2]:
                if isinstance(c, dict):
                    sample_comps.append({
                        "source": c.get("source", ""),
                        "equipment": c.get("description") or c.get("equipment", ""),
                        "year": c.get("year", ""),
                        "location": c.get("location", ""),
                        "sold_price": c.get("price") or c.get("sold_price", ""),
                    })
        cat_summaries.append({
            "category": cat,
            "unit_count": len(items),
            "fmv_low_total": sum(fmv_lows),
            "fmv_high_total": sum(fmv_highs),
            "fmv_low_per_unit_avg": (sum(fmv_lows) / len(items)) if items else 0,
            "fmv_high_per_unit_avg": (sum(fmv_highs) / len(items)) if items else 0,
            "sample_titles": sample_titles,
            "sample_comps": sample_comps[:5],
        })

    payload = {
        "client": client,
        "total_units": summary.get("total", len(results)),
        "total_fmv_low": summary.get("total_fmv_low", 0),
        "total_fmv_high": summary.get("total_fmv_high", 0),
        "buyer_offer": buyer_offer,
        "categories": cat_summaries,
    }

    content = (
        f"PORTFOLIO PRICING DATA (grouped by category):\n{json.dumps(payload, indent=2, default=str)}\n\n"
        f"CLIENT: {client}\n"
        f"INSTRUCTIONS: Write a Tier 2 multi-item Support Document for the portfolio above. "
        f"Produce one category narrative per category, rolled-up identification parameters, "
        f"3-5 representative comps with key observations, and 5-7 valuation factors covering "
        f"bulk-sale dynamics. Match the JSON schema exactly."
    )

    return [{"role": "user", "content": content}]


def build_report_messages(
    structured: dict,
    response_text: str,
    user_message: str,
    client: str,
    tier: int = 3,
) -> list[dict]:
    """Build the user messages for the report-generation Claude pass."""
    tier_instructions = {
        2: (
            "Write a Tier 2 (support-level) report. Include: executive_summary, "
            "equipment_description (brief overview, key specs only), "
            "valuation_methodology (RCN summary + depreciation with factors), "
            "market_comparables (top 3-4 comps + brief analysis), "
            "fair_market_value (scenarios + list pricing), "
            "assumptions (5-6 equipment-specific), sources."
        ),
        3: (
            "Write a Tier 3 (full) report. Include ALL sections at maximum depth: "
            "executive_summary (2-3 paragraphs), equipment_description (full specs table), "
            "valuation_methodology (component-level RCN breakdown + all depreciation factors), "
            "market_comparables (all comps + 2-3 paragraph analysis), "
            "fair_market_value (all scenarios + overhaul economics if applicable + list pricing), "
            "market_context (5+ location-specific bullets), "
            "assumptions (8+ equipment-specific), sources (with specifics)."
        ),
    }
    instruction = tier_instructions.get(tier, tier_instructions[3])

    content = (
        f"PRICING DATA (structured JSON):\n{json.dumps(structured, indent=2)}\n\n"
        f"AI RESPONSE NARRATIVE:\n{response_text}\n\n"
        f"USER EQUIPMENT DESCRIPTION:\n{user_message}\n\n"
        f"CLIENT: {client}\n"
        f"TIER: {tier}\n\n"
        f"INSTRUCTIONS: {instruction}\n\n"
        "Use the structured data and response text to produce equipment-specific "
        f"content. Write the report sections for a Tier {tier} report for {client}."
    )

    return [{"role": "user", "content": content}]
