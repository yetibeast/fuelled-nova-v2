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
