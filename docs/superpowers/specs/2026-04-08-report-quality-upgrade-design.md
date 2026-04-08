# Report Quality Upgrade — Design Spec

## Problem

Current reports are scaffolding around sparse JSON fields. Example client deliverables (ARC pump, Ovintiv VRU, SCR Ariel compressor) show senior-appraiser-quality writing: component-level RCN breakdowns, equipment-specific depreciation rationale, named comparable analysis, overhaul economics, and location-specific assumptions. The gap between what we produce and what clients expect is significant.

## Root Cause

Claude's pricing response contains rich reasoning in its `response_text` narrative, but the report generators (`report.py`, `report_support.py`, `report_onepager.py`) only read the `structured` JSON fields — which are sparse summaries (FMV range, a few factors, comp URLs). The narrative reasoning is discarded.

## Solution

### Tier 1 (One-Pager): No extra API call

Render existing structured data better. Add:
- FMV range table (already exists)
- Depreciation factors table with rationale (from `structured.valuation.factors[]`)
- Top 2-3 comparable listings (from `structured.comparables[]`)
- Brief methodology sentence ("RCN-D approach using [source], adjusted for age, condition, and market factors")
- Confidence indicator

Data source: `structured` JSON + `response_text` (rendered as-is for methodology summary).

Output: 2-3 page DOCX with substance, not just a bare table.

### Tiers 2 & 3: Dedicated Claude Report Pass

When user clicks "Export Tier 2" or "Export Tier 3", the system:

1. Sends pricing results (structured data + response_text + user_message) to a new `POST /api/reports/generate` flow
2. Calls Claude with a **report-specific prompt** that includes:
   - The pricing structured data (FMV, RCN, comps, factors)
   - The AI's original response_text narrative
   - The user's equipment description
   - Client name (from export dialog)
   - Tier level (determines which sections to write)
   - Few-shot examples extracted from the gold-standard reports
3. Claude returns a structured JSON with report-quality content per section
4. The DOCX generator renders those sections with professional formatting

### Report Prompt Design

The report prompt instructs Claude to write as a senior equipment appraiser producing a client deliverable. Key instructions:

- **Be equipment-specific, not generic.** "The Ariel JGP frame is uncommon in new builds — most packagers now start at JGJ/2" not "compressors depreciate over time."
- **Name your sources.** "RCN derived from CSM Pump Packaging quote" or "Fuelled database of 2,141 compressor listings."
- **Show the math.** "$275,000 × 0.20 × 0.50 × 1.00 × 1.00 = $27,500"
- **Explain each depreciation factor.** Not just "Age: 0.20" but "Age Depreciation (17 years): 0.20 — Standard 16-20 year band for rotating equipment."
- **Analyze comparables, don't just list them.** "The $50K CAT G3306NA/Gemini is the best comp — same engine, same stages. The $145K Ariel JGJ/2 sets the ceiling."
- **Equipment-specific assumptions.** Not boilerplate "condition assumed good" but "ABSA registration status has not been confirmed. Registered equipment commands a 10% premium."
- **Include cost considerations.** Transport, re-certification, overhaul estimates with dollar ranges.

### Claude Report Response Schema

```json
{
  "executive_summary": "2-3 paragraphs: who requested, what equipment, key findings, FMV range",
  "equipment_description": {
    "overview": "paragraph describing the equipment in context",
    "specs_table": [{"component": "str", "specification": "str"}, ...],
    "notes": "any individual unit details or condition notes"
  },
  "valuation_methodology": {
    "approach": "paragraph explaining RCN-D methodology choice",
    "rcn_derivation": {
      "narrative": "how RCN was determined (OEM quote, scaling, database)",
      "components": [{"component": "str", "cost_range": "str"}, ...],
      "total_rcn": "str",
      "notes": "escalation factors, source references"
    },
    "depreciation": {
      "formula": "str showing the full calculation",
      "factors": [{"factor": "str", "multiplier": "number", "rationale": "str"}, ...],
      "notes": "any special considerations (age vs condition tension, etc.)"
    }
  },
  "market_comparables": {
    "overview": "paragraph on market data availability and relevance",
    "listings": [{"description": "str", "price": "str", "year": "str", "location": "str", "source": "str", "notes": "str"}, ...],
    "analysis": "2-3 paragraphs analyzing what the comps tell us — best comp, floor, ceiling, adjustments"
  },
  "fair_market_value": {
    "summary": "paragraph with FMV range and confidence",
    "scenarios": [{"scenario": "str", "fmv_low": "number", "fmv_high": "number", "confidence": "str"}, ...],
    "list_pricing": {"fmv_midpoint": "number", "list_premium": "str", "recommended_list": "number", "walkaway_floor": "number"},
    "overhaul_economics": "paragraph if applicable (cost to overhaul, post-overhaul value)"
  },
  "market_context": "3-5 bullet points on location-specific demand, regulatory environment, buyer pool",
  "assumptions": ["equipment-specific assumption 1", "assumption 2", ...],
  "disclaimer": "standard legal disclaimer",
  "sources": ["source 1 with specifics", "source 2", ...]
}
```

### Section Inclusion by Tier

| Section | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| Cover page (client, date, ref) | No | Yes | Yes |
| FMV summary table | Yes (from structured) | Yes (from Claude) | Yes (from Claude) |
| Factors table + reasoning | Yes (from structured) | Yes (from Claude) | Yes (from Claude) |
| Top 2-3 comps | Yes (from structured) | Yes (from Claude) | Yes (from Claude) |
| Executive Summary | No | Yes | Yes |
| Equipment Description + specs | No | Brief | Full with specs table |
| RCN Breakdown (components) | No | Summary | Component-level table |
| Comparables Analysis narrative | No | Brief | Full (best comp, floor, ceiling) |
| Fair Market Value + scenarios | FMV range only | Yes | Yes + overhaul economics |
| Market Context | No | No | Yes (bullets) |
| Assumptions | No | Standard (5-6) | Equipment-specific (8+) |
| Disclaimer + signature | Confidentiality line | Yes | Full |
| Sources / Appendix | No | Brief | Full |

### File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/app/pricing_v2/report_content.py` | Claude report pass — sends prompt, returns structured sections |
| Create | `backend/app/pricing_v2/report_prompt.py` | Report-specific prompt with few-shot examples |
| Modify | `backend/app/pricing_v2/report_onepager.py` | Render factors, comps, methodology from structured data |
| Modify | `backend/app/pricing_v2/report_support.py` | Use Claude report sections instead of sparse structured data |
| Modify | `backend/app/pricing_v2/report.py` | Use Claude report sections for all content |
| Modify | `backend/app/api/reports.py` | Call report_content for Tier 2/3 before generating DOCX |

### Cost & Performance

- **Tier 1:** No API call. Instant generation. $0.
- **Tier 2:** One Claude Sonnet call. ~4K input + ~3K output = ~$0.06. ~20 seconds.
- **Tier 3:** One Claude Sonnet call. ~6K input + ~5K output = ~$0.09. ~30 seconds.
- **Total per-report cost:** Negligible for a client deliverable.

### Few-Shot Examples

The report prompt includes condensed versions of the gold-standard reports as few-shot examples. These are stored in `backend/app/pricing_v2/report_examples/` as text files:
- `example_pump_valuation.txt` — ARC Fresh Water Pump (component RCN, hours-based adjustment)
- `example_vru_valuation.txt` — Ovintiv VRU (age vs condition tension, obsolescence)
- `example_compressor_valuation.txt` — SCR Ariel JGP (market comp analysis, overhaul economics)

Each example is ~800-1000 tokens, trimmed to the key sections. The prompt selects the most relevant example based on equipment category.

### Quality Criteria

A generated report should:
1. Read like it was written by a senior appraiser, not assembled from template fragments
2. Name specific equipment models, manufacturers, and market references
3. Show the math — RCN × factor × factor = FMV, with dollar amounts
4. Explain why each depreciation factor was chosen for this specific equipment
5. Analyze comparables, not just list them
6. Include equipment-specific assumptions (not boilerplate)
7. Match the professional formatting of the existing DOCX generators (navy headers, orange accents, Fuelled branding)
