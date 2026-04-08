# Report Quality Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade all three report tiers to match the quality of the example client deliverables (ARC pump, Ovintiv VRU, SCR Ariel compressor reports).

**Architecture:** Tier 1 uses existing structured data rendered with more substance. Tiers 2 & 3 make a second Claude API call with a report-specific prompt + few-shot examples, returning structured sections that the DOCX generators render. New files: `report_content.py` (Claude report pass orchestrator), `report_prompt.py` (prompt + few-shot examples). Modified files: all three report generators + `reports.py` API.

**Tech Stack:** Python, python-docx, Anthropic SDK (Claude Sonnet), FastAPI

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `backend/app/pricing_v2/report_content.py` | Claude report pass — sends prompt, parses response into sections |
| Create | `backend/app/pricing_v2/report_prompt.py` | Report prompt text + few-shot example builder |
| Modify | `backend/app/pricing_v2/report_onepager.py` | Add factors table, top comps, methodology line |
| Modify | `backend/app/pricing_v2/report_support.py` | Use Claude report sections for all content |
| Modify | `backend/app/pricing_v2/report.py` | Use Claude report sections for all content |
| Modify | `backend/app/api/reports.py` | Call report_content for Tier 2/3 before DOCX generation |

---

## Chunk 1: Report Content Engine + Prompt

### Task 1: Create report prompt with few-shot examples

**Files:**
- Create: `backend/app/pricing_v2/report_prompt.py`

This file contains the report-specific system prompt and builds the few-shot examples from condensed versions of the gold-standard reports.

- [ ] **Step 1: Create report_prompt.py**

The prompt instructs Claude to write as a senior equipment appraiser producing a client deliverable. It includes condensed examples from the ARC pump and SCR Ariel compressor reports (trimmed to key sections to stay under 2K tokens per example). The function `build_report_prompt()` returns the system prompt, and `build_report_messages()` returns the user message with all context (structured data, response_text, user_message, client name, tier level).

Key prompt instructions:
- Be equipment-specific, not generic
- Name sources (OEM, database size, specific listings)
- Show the math: RCN × factor × factor = FMV with dollar amounts
- Each depreciation factor gets equipment-specific rationale (not "applied per standard curves")
- Analyze comparables — explain why each is relevant, what it tells you
- Equipment-specific assumptions (not boilerplate "condition assumed good")
- Include cost considerations with dollar ranges (transport, re-cert, overhaul)
- Condition grading with PASC-style letter grades (A/B/C/D)

The response schema matches the spec: `executive_summary`, `equipment_description`, `valuation_methodology` (with `rcn_derivation.components[]` and `depreciation.factors[]`), `market_comparables` (with `analysis`), `fair_market_value` (with `scenarios[]` and `overhaul_economics`), `market_context`, `assumptions[]`, `sources[]`.

Few-shot examples are stored inline as string constants (not separate files) to keep deployment simple. Each is ~800 tokens trimmed to the distinctive sections: the RCN component breakdown, the depreciation factors table, and the comparable analysis.

- [ ] **Step 2: Verify module imports**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2 && PYTHONPATH=backend python3 -c "from app.pricing_v2.report_prompt import build_report_prompt, build_report_messages; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/report_prompt.py
git commit -m "feat: report prompt with few-shot examples from gold-standard reports"
```

---

### Task 2: Create report content engine

**Files:**
- Create: `backend/app/pricing_v2/report_content.py`

This module calls Claude with the report prompt and parses the JSON response into a dict of report sections. It's called by the API layer for Tier 2 and Tier 3 reports.

- [ ] **Step 1: Create report_content.py**

The function `generate_report_content(structured, response_text, user_message, client, tier)` does:
1. Builds the prompt via `report_prompt.build_report_prompt()`
2. Builds the messages via `report_prompt.build_report_messages(structured, response_text, user_message, client, tier)`
3. Calls Claude Sonnet via Anthropic SDK (same client as service.py)
4. Parses the JSON response into a dict matching the report schema
5. Falls back gracefully if Claude returns malformed JSON — uses the raw structured data instead
6. Returns the sections dict

The function is async and uses the same Anthropic client pattern as `service.py`. It does NOT use tools — just a single message/response exchange.

Key implementation details:
- Model: `claude-sonnet-4-20250514` (same as pricing)
- Max tokens: 4096 (Tier 2) or 6144 (Tier 3)
- Temperature: 0.3 (more deterministic for report writing)
- Response is requested as JSON via system prompt instruction (not tool_use)
- Timeout: 60 seconds
- On failure: returns None, and DOCX generators fall back to current behavior (sparse structured data)

- [ ] **Step 2: Test with a real pricing result**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2
PYTHONPATH=backend ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY backend/.env | cut -d= -f2) python3 -c "
import asyncio, json
from app.pricing_v2.report_content import generate_report_content

# Use a sample structured result
structured = {
    'valuation': {'fmv_low': 25000, 'fmv_high': 40000, 'fmv_mid': 32500, 'rcn': 275000, 'confidence': 'MEDIUM', 'currency': 'CAD', 'title': 'Ariel JGP 2-Stage Gas Compressor Package', 'factors': [{'label': 'Age Depreciation', 'value': 0.20, 'rationale': '~17 years old'}, {'label': 'Condition', 'value': 0.50, 'rationale': 'Needs overhaul'}]},
    'comparables': [{'title': 'CAT G3306NA / Gemini H302', 'price': 50000, 'year': '1998', 'location': 'Vulcan, AB', 'source': 'Kijiji'}],
    'risks': ['Requires frame overhaul', 'Unknown operating hours'],
    'sources': ['Fuelled marketplace database', 'Industry RCN benchmarks'],
}
response_text = 'This is a 2-stage gas compressor package requiring overhaul...'

sections = asyncio.run(generate_report_content(structured, response_text, 'Price an Ariel JGP compressor package', 'Strathcona Resources', tier=3))
print(json.dumps(sections, indent=2)[:2000])
"
```

Verify: output contains `executive_summary`, `equipment_description`, `valuation_methodology` with `rcn_derivation.components` and `depreciation.factors`, `market_comparables` with `analysis`, `fair_market_value`, `assumptions`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/report_content.py
git commit -m "feat: report content engine — Claude report pass for Tier 2/3"
```

---

## Chunk 2: Tier 1 One-Pager Upgrade

### Task 3: Upgrade one-pager to include factors, comps, methodology

**Files:**
- Modify: `backend/app/pricing_v2/report_onepager.py`

Currently the one-pager is just a title + FMV table + basis of value line. Upgrade to include:
1. Equipment description line (from `user_message`)
2. FMV summary table (existing, keep)
3. **NEW: Depreciation factors table** — from `structured.valuation.factors[]` with columns: Factor | Multiplier | Rationale
4. **NEW: Top 3 comparable listings** — from `structured.comparables[]` with columns: Description | Price | Location | Source
5. **NEW: Methodology sentence** — "Valued using RCN-D methodology. RCN of $X adjusted for [list factor labels]. Validated against N market comparables."
6. Basis of value (existing, keep)
7. Confidentiality footer (existing, keep)

No extra API call. All data comes from existing structured JSON.

- [ ] **Step 1: Add factors table after FMV table**

After the existing FMV summary table (line ~103), add a "Valuation Factors" section:
- Heading: "Valuation Factors" (navy, 11pt bold)
- Table with columns: Factor | Multiplier | Rationale
- Data from `structured.get("valuation", {}).get("factors", [])`
- Skip if empty

- [ ] **Step 2: Add top comparables**

After the factors table, add a "Market Comparables" section:
- Heading: "Market Comparables" (navy, 11pt bold)  
- Table with columns: Description | Price | Location | Source
- Data from `structured.get("comparables", [])[:3]`
- Skip if empty

- [ ] **Step 3: Add methodology line**

Before the "Basis of Value" line, add a methodology summary:
- "Methodology: Replacement Cost New less Depreciation (RCN-D). RCN of {rcn} adjusted by {N} factors. Validated against {M} market comparable(s) from the Fuelled database."
- Pull RCN from `val.get("rcn")`, factor count from `len(val.get("factors", []))`, comp count from `len(structured.get("comparables", []))`

- [ ] **Step 4: Test one-pager generation locally**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2
PYTHONPATH=backend python3 -c "
from app.pricing_v2.report_onepager import generate_onepager
structured = {
    'valuation': {'fmv_low': 25000, 'fmv_high': 40000, 'fmv_mid': 32500, 'rcn': 275000, 'currency': 'CAD', 'factors': [{'label': 'Age', 'value': 0.20, 'rationale': '17 years'}, {'label': 'Condition', 'value': 0.50, 'rationale': 'Needs overhaul'}]},
    'comparables': [{'title': 'CAT G3306NA / Gemini', 'price': 50000, 'location': 'Vulcan, AB', 'source': 'Kijiji'}],
}
docx_bytes = generate_onepager(structured, 'Ariel JGP 2-Stage Gas Compressor')
with open('/tmp/test_onepager.docx', 'wb') as f:
    f.write(docx_bytes)
print(f'Generated {len(docx_bytes)} bytes -> /tmp/test_onepager.docx')
"
```

Open `/tmp/test_onepager.docx` and verify it has: FMV table, factors table, comps table, methodology line.

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/report_onepager.py
git commit -m "feat: Tier 1 one-pager shows factors, comps, and methodology"
```

---

## Chunk 3: Tier 2 Support Report Upgrade

### Task 4: Rewrite support report to use Claude sections

**Files:**
- Modify: `backend/app/pricing_v2/report_support.py`
- Modify: `backend/app/api/reports.py`

The Tier 2 report currently renders sparse structured data. Rewrite it to accept a `report_sections` dict (from the Claude report pass) and render rich content.

- [ ] **Step 1: Update reports.py to call report_content for Tier 2**

In the `tier == 2` branch of `generate()`, before calling `generate_support_report()`:
1. Import and call `generate_report_content()`
2. Pass the sections dict to `generate_support_report()` as a new `sections` parameter
3. The function signature becomes: `generate_support_report(results, summary, client, sections=None)`
4. If `sections` is None (fallback), use current behavior

- [ ] **Step 2: Rewrite support report sections to use Claude content**

When `sections` is provided, each section renders Claude's content instead of sparse structured data:

- **Cover page**: Use `sections.get("executive_summary")` for intro paragraph
- **Equipment Description**: Use `sections["equipment_description"]["overview"]` and `sections["equipment_description"]["specs_table"]`
- **RCN Methodology**: Use `sections["valuation_methodology"]["rcn_derivation"]` — component table + narrative
- **Depreciation Factors**: Use `sections["valuation_methodology"]["depreciation"]["factors"]` — table with rationale
- **Comparables**: Use `sections["market_comparables"]["listings"]` for table AND `sections["market_comparables"]["analysis"]` for commentary paragraph
- **FMV + Scenarios**: Use `sections["fair_market_value"]` with scenario table
- **Assumptions**: Use `sections["assumptions"]` (equipment-specific)
- **Sources**: Use `sections["sources"]`
- **Disclaimer**: Standard text (no change)

Keep the existing rendering functions (`_heading`, `_table`, etc.) — just feed them richer data.

- [ ] **Step 3: Test Tier 2 generation locally**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2
PYTHONPATH=backend ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY backend/.env | cut -d= -f2) python3 -c "
import asyncio
from app.pricing_v2.report_content import generate_report_content
from app.pricing_v2.report_support import generate_support_report

structured = {
    'valuation': {'fmv_low': 25000, 'fmv_high': 40000, 'fmv_mid': 32500, 'rcn': 275000, 'confidence': 'MEDIUM', 'currency': 'CAD', 'title': 'Ariel JGP Compressor', 'factors': [{'label': 'Age', 'value': 0.20, 'rationale': '17 years'}, {'label': 'Condition', 'value': 0.50, 'rationale': 'Needs overhaul'}]},
    'comparables': [{'title': 'CAT G3306NA / Gemini', 'price': 50000, 'year': '1998', 'location': 'Vulcan, AB', 'source': 'Kijiji'}],
    'risks': ['Overhaul required'], 'sources': ['Fuelled database'],
}
results = [{'structured': structured, 'title': 'Ariel JGP Compressor', 'confidence': 'MEDIUM'}]
summary = {'total': 1, 'completed': 1, 'failed': 0, 'total_fmv_low': 25000, 'total_fmv_high': 40000}

sections = asyncio.run(generate_report_content(structured, 'A compressor needing overhaul...', 'Price an Ariel JGP', 'Strathcona Resources', tier=2))
docx_bytes = generate_support_report(results, summary, 'Strathcona Resources', sections=sections)
with open('/tmp/test_tier2.docx', 'wb') as f:
    f.write(docx_bytes)
print(f'Generated {len(docx_bytes)} bytes -> /tmp/test_tier2.docx')
"
```

Open and verify: executive summary paragraph, equipment description, RCN component table, depreciation factors with rationale, comparable analysis paragraph.

- [ ] **Step 4: Commit**

```bash
git add backend/app/pricing_v2/report_support.py backend/app/api/reports.py
git commit -m "feat: Tier 2 report uses Claude report pass for rich content"
```

---

## Chunk 4: Tier 3 Full Assessment Upgrade

### Task 5: Rewrite full report to use Claude sections

**Files:**
- Modify: `backend/app/pricing_v2/report.py`
- Modify: `backend/app/api/reports.py`

Same pattern as Tier 2 but the full report includes all sections: market context, scenario analysis, overhaul economics, equipment-specific assumptions.

- [ ] **Step 1: Update reports.py to call report_content for Tier 3**

In the `tier == 3` branch, call `generate_report_content()` and pass sections to `generate_report()`.
New signature: `generate_report(structured, response_text, user_message, sections=None)`

- [ ] **Step 2: Rewrite report sections to use Claude content**

When `sections` is provided:

- **Executive Summary**: Replace the template summary with `sections["executive_summary"]` rendered as 2-3 paragraphs
- **Equipment Description**: Use `sections["equipment_description"]["overview"]` as narrative + `specs_table` as a proper Component/Specification table (matching the example reports)
- **Valuation Methodology / RCN**: Use `sections["valuation_methodology"]["rcn_derivation"]` — narrative paragraph + component cost breakdown table + notes
- **Depreciation**: Use `sections["valuation_methodology"]["depreciation"]` — formula string rendered bold + factors table with rationale
- **Market Comparables**: Use `sections["market_comparables"]["listings"]` for table + `sections["market_comparables"]["analysis"]` for 2-3 paragraphs of comparable analysis (best comp, floor, ceiling)
- **Fair Market Value**: Use `sections["fair_market_value"]` — scenarios table + list pricing table + overhaul economics paragraph
- **Market Context**: Use `sections["market_context"]` — render as bullet points
- **Assumptions**: Use `sections["assumptions"]` — equipment-specific numbered list
- **Sources**: Use `sections["sources"]`
- **Optional sections**: Remove the generic optional sections block (market_context, equipment_context, etc. from structured data). The Claude report pass covers these much better.

Keep: Cover page, disclaimer, signature block, all formatting helpers.

- [ ] **Step 3: Test Tier 3 generation locally**

Same test pattern as Tier 2 but with `tier=3` and open the output to verify all sections are populated with rich, equipment-specific content.

- [ ] **Step 4: Commit**

```bash
git add backend/app/pricing_v2/report.py backend/app/api/reports.py
git commit -m "feat: Tier 3 full report uses Claude report pass for appraiser-quality content"
```

---

## Chunk 5: Integration Test + Deploy

### Task 6: End-to-end test all three tiers

- [ ] **Step 1: Start local backend**

```bash
cd /Users/lynch/Documents/projects/fuelled-nova-v2
PYTHONPATH=backend DATABASE_URL="postgresql+asyncpg://postgres:tFUtNBaGcBAzVFocfLriTjxwkxRTQKsZ@trolley.proxy.rlwy.net:34278/railway" ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY backend/.env | cut -d= -f2) JWT_SECRET=$(grep JWT_SECRET backend/.env | cut -d= -f2) PRICING_V2_ENABLED=true python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8100
```

- [ ] **Step 2: Run a pricing query and generate all 3 tiers**

```bash
TOKEN=$(curl -s -X POST http://localhost:8100/api/auth/login -H "Content-Type: application/json" -d '{"email":"curtis@arcanosai.com","password":"fuelled2026"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Run pricing
RESULT=$(curl -s -X POST http://localhost:8100/api/price -H "Authorization: Bearer $TOKEN" -F "message=Price this sour skid package https://www.fuelled.com/listings/natural-gas-pressure-reduction-sour-skid-package-15835" -F "history=[]")

# Generate Tier 1
curl -s -X POST http://localhost:8100/api/reports/generate -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"tier\":1,\"type\":\"single\",\"data\":$RESULT,\"client\":\"Test Client\"}" -o /tmp/tier1.docx

# Generate Tier 2
curl -s -X POST http://localhost:8100/api/reports/generate -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"tier\":2,\"type\":\"single\",\"data\":[$RESULT],\"client\":\"Test Client\"}" -o /tmp/tier2.docx

# Generate Tier 3
curl -s -X POST http://localhost:8100/api/reports/generate -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"tier\":3,\"type\":\"single\",\"data\":$RESULT,\"client\":\"Test Client\"}" -o /tmp/tier3.docx

ls -la /tmp/tier*.docx
```

- [ ] **Step 3: Open and review each report**

Verify against the example reports:
- **Tier 1**: Has FMV table, factors table with rationale, top comps, methodology line. ~2-3 pages.
- **Tier 2**: Has executive summary, equipment description, RCN breakdown, depreciation factors, comparable analysis, FMV scenarios, assumptions. ~5-6 pages.
- **Tier 3**: Has all Tier 2 sections plus market context, overhaul economics, component-level RCN, full comparable analysis, equipment-specific assumptions. ~10+ pages.

- [ ] **Step 4: Commit + push + deploy**

```bash
git add -A
git commit -m "feat: report quality upgrade — all 3 tiers match client deliverable standard"
git push origin main
railway up --service backend --detach -m "Report quality upgrade"
```

---

## Key Testing Checklist

For each tier, verify:
- [ ] RCN source is named (not "Fuelled RCN tables" generically, but e.g. "Component build-up based on industry benchmarks for 2-stage reciprocating compressors")
- [ ] Each depreciation factor has equipment-specific rationale (not "applied per standard curves")
- [ ] Comparable analysis explains relevance (not just a table)
- [ ] Assumptions are equipment-specific (not boilerplate)
- [ ] Dollar math is shown (RCN × factors = FMV)
- [ ] Professional formatting (navy headers, orange accents, Arial font, Fuelled branding)
- [ ] Tier 1 has no extra API call (fast generation)
- [ ] Tiers 2/3 gracefully fall back if Claude call fails
