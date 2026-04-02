# Portfolio Assessment & Report Quality Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the pricing agent with portfolio assessment workflow, three report tiers, richer structured output, and location-aware reasoning — matching the quality of the example reports.

**Architecture:** Prompt-first approach. Claude's reasoning produces richer structured JSON. Report generators render what the agent gives them. Batch infrastructure upgraded with async job tracking and portfolio synthesis. Frontend gets a results table for multi-item jobs and a report tier picker.

**Tech Stack:** Python/FastAPI (backend), Next.js/React/TypeScript (frontend), python-docx (reports), Anthropic SDK (Claude API)

**Spec:** `docs/superpowers/specs/2026-04-01-portfolio-assessment-design.md`

---

## Chunk 1: Backend Foundation (report_common, normalize, quality guide)

These are shared utilities that everything else depends on.

### Task 1: Shared report helpers (report_common.py)

**Files:**
- Create: `backend/app/pricing_v2/report_common.py`
- Test: `backend/tests/test_report_common.py`

- [ ] **Step 1: Write failing tests for _price()**

```python
# backend/tests/test_report_common.py
def test_price_cad():
    from app.pricing_v2.report_common import price_fmt
    assert price_fmt(150000, "CAD") == "$150,000 CAD"

def test_price_usd():
    from app.pricing_v2.report_common import price_fmt
    assert price_fmt(150000, "USD") == "$150,000 USD"

def test_price_none():
    from app.pricing_v2.report_common import price_fmt
    assert price_fmt(None, "CAD") == "[N/A]"

def test_price_zero():
    from app.pricing_v2.report_common import price_fmt
    assert price_fmt(0, "CAD") == "[N/A]"

def test_price_default_currency():
    from app.pricing_v2.report_common import price_fmt
    assert price_fmt(50000) == "$50,000 CAD"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=backend python3 -m pytest backend/tests/test_report_common.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Create report_common.py with shared helpers**

```python
# backend/app/pricing_v2/report_common.py
"""Shared helpers for all report generators."""
from __future__ import annotations
import datetime
from docx.shared import Pt, RGBColor
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# ── Colour palette ───────────────────────────────────────────
NAVY = RGBColor(0x1A, 0x1A, 0x2E)
BLUE = RGBColor(0x00, 0x77, 0xB6)
ORANGE_HEX = "E85D04"
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY_HEX = "F5F5F5"
MUTED = RGBColor(0x66, 0x66, 0x66)


def price_fmt(n, currency: str = "CAD") -> str:
    if n is None or n == 0:
        return "[N/A]"
    return f"${n:,.0f} {currency}"


def ref_number(prefix: str = "FV") -> str:
    d = datetime.date.today()
    return f"{prefix}-{d.year}-{d.month:02d}{d.day:02d}"


def today_str() -> str:
    return datetime.date.today().strftime("%B %d, %Y")


def shade(cell, hex_color: str):
    cell._tc.get_or_add_tcPr().append(
        parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'))


def navy_row(table, idx: int):
    for cell in table.rows[idx].cells:
        shade(cell, "1A1A2E")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.color.rgb = WHITE
                r.font.bold = True


def alt_shade(table, start: int = 1):
    for i in range(start, len(table.rows)):
        if i % 2 == 0:
            for cell in table.rows[i].cells:
                shade(cell, GRAY_HEX)


def font(run, size: int = 10, bold: bool = False, italic: bool = False, color=None):
    run.font.name = "Arial"
    run.font.size = Pt(size)
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if color:
        run.font.color.rgb = color


def border_xml(tag: str, color: str = ORANGE_HEX, sz: str = "12") -> str:
    return (f'<w:pBdr {nsdecls("w")}>'
            f'<w:{tag} w:val="single" w:sz="{sz}" w:space="1" w:color="{color}"/>'
            f'</w:pBdr>')


def divider(doc):
    p = doc.add_paragraph()
    p._element.get_or_add_pPr().append(parse_xml(border_xml("bottom")))


DISCLAIMER = (
    "This document is prepared for the sole use of the intended recipient and contains "
    "confidential information. Fair Market Value represents the estimated price at which "
    "the equipment would change hands between a willing buyer and a willing seller, "
    "neither being under compulsion to buy or sell and both having reasonable knowledge "
    "of relevant facts. All values are estimates based on available market data and "
    "professional judgment."
)

FOOTER_LINE = "Confidential | Fuelled Energy Marketing Inc. | valuations@fuelled.com"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=backend python3 -m pytest backend/tests/test_report_common.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/report_common.py backend/tests/test_report_common.py
git commit -m "feat: add shared report helpers (report_common.py)"
```

### Task 2: Structured output normalization

**Files:**
- Create: `backend/app/pricing_v2/normalize.py`
- Test: `backend/tests/test_normalize.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_normalize.py
from app.pricing_v2.normalize import normalize_structured

def test_empty_input():
    result = normalize_structured({})
    assert result["valuation"] is not None
    assert result["comparables"] == []
    assert result["risks"] == []
    assert result["market_context"] is None
    assert result["assumptions"] == []
    assert result["sources"] == []

def test_full_input_unchanged():
    data = {
        "valuation": {"fmv_low": 100000, "fmv_high": 200000, "confidence": "HIGH", "currency": "CAD"},
        "comparables": [{"title": "Test", "price": 150000}],
        "risks": ["Risk 1"],
        "market_context": "Strong demand",
        "equipment_context": "Common frame",
        "condition_assessment": "Good",
        "cost_considerations": None,
        "scenario_analysis": None,
        "marketing_guidance": None,
        "missing_data_impact": None,
        "key_value_drivers": ["Driver 1"],
        "assumptions": ["Assumption 1"],
        "sources": ["Fuelled.com"],
    }
    result = normalize_structured(data)
    assert result["valuation"]["fmv_low"] == 100000
    assert result["market_context"] == "Strong demand"
    assert result["key_value_drivers"] == ["Driver 1"]

def test_valuation_defaults():
    result = normalize_structured({"valuation": {"fmv_low": 50000}})
    v = result["valuation"]
    assert v["fmv_low"] == 50000
    assert v["fmv_high"] is None
    assert v["currency"] == "CAD"
    assert v["confidence"] == "LOW"

def test_currency_preserved():
    result = normalize_structured({"valuation": {"currency": "USD", "fmv_low": 100}})
    assert result["valuation"]["currency"] == "USD"
```

- [ ] **Step 2: Run tests — expect fail**

Run: `PYTHONPATH=backend python3 -m pytest backend/tests/test_normalize.py -v`

- [ ] **Step 3: Implement normalize.py**

```python
# backend/app/pricing_v2/normalize.py
"""Normalize structured output from pricing agent — ensures all fields exist."""
from __future__ import annotations

_VALUATION_DEFAULTS = {
    "fmv_low": None, "fmv_high": None, "fmv_mid": None,
    "rcn": None, "confidence": "LOW", "currency": "CAD",
    "list_price": None, "walkaway": None, "factors": [],
    "type": None, "title": None,
}

_TOP_LEVEL_DEFAULTS = {
    "valuation": {},
    "comparables": [],
    "risks": [],
    "market_context": None,
    "equipment_context": None,
    "condition_assessment": None,
    "cost_considerations": None,
    "scenario_analysis": None,
    "marketing_guidance": None,
    "missing_data_impact": None,
    "key_value_drivers": [],
    "assumptions": [],
    "sources": [],
}


def normalize_structured(data: dict) -> dict:
    """Ensure all expected fields exist with sensible defaults."""
    result = {}
    for key, default in _TOP_LEVEL_DEFAULTS.items():
        val = data.get(key)
        if val is None:
            result[key] = default if isinstance(default, (list, dict)) else default
        else:
            result[key] = val

    # Normalize valuation sub-fields
    raw_val = result.get("valuation") or {}
    normalized_val = {}
    for key, default in _VALUATION_DEFAULTS.items():
        normalized_val[key] = raw_val.get(key, default)
    result["valuation"] = normalized_val

    return result
```

- [ ] **Step 4: Run tests — expect pass**

Run: `PYTHONPATH=backend python3 -m pytest backend/tests/test_normalize.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/normalize.py backend/tests/test_normalize.py
git commit -m "feat: add structured output normalization"
```

### Task 3: Quality reference guide for prompt

**Files:**
- Create: `backend/app/pricing_v2/references/report_quality_guide.md`
- Modify: `backend/app/pricing_v2/prompts.py` (add to _SECTIONS)

- [ ] **Step 1: Create report_quality_guide.md**

Write a ~2K token markdown file with excerpted examples of "what good looks like" for each report section type. Extract the best examples from the 4 .docx example reports. Sections:
- Executive Summary example (from ARC pump report)
- Market Context example (from Ovintiv VRU — regulatory demand, buyer pool)
- Condition Assessment example (from Ovintiv VRU — "Age vs. Condition Problem")
- Comparable Analysis example (from SCR Ariel — ask vs. transaction, convergence)
- Cost Considerations example (from ARC — transport $15K-$30K, ABSA re-cert)
- Marketing Guidance example (from Ovintiv VRU — "lead with unused/zero hours")

Read the example reports to extract real excerpts. Keep total under 2,500 words.

- [ ] **Step 2: Add to _SECTIONS in prompts.py**

Add `("REPORT QUALITY GUIDE", "report_quality_guide.md")` to the `_SECTIONS` list in `prompts.py`.

- [ ] **Step 3: Clear the prompt cache**

The `_cached_prompt` global needs to be `None` to pick up the new section. This happens automatically on server restart.

- [ ] **Step 4: Verify prompt loads**

```bash
PYTHONPATH=backend python3 -c "from app.pricing_v2.prompts import build_system_prompt; p = build_system_prompt(); print(f'Prompt length: {len(p)} chars'); assert 'REPORT QUALITY GUIDE' in p; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/references/report_quality_guide.md backend/app/pricing_v2/prompts.py
git commit -m "feat: add report quality guide to system prompt"
```

---

## Chunk 2: Enhanced System Prompt & Structured Output

### Task 4: Upgrade system prompt for richer output

**Files:**
- Modify: `backend/app/pricing_v2/prompts.py`

- [ ] **Step 1: Update _HEADER with new JSON schema**

Replace the existing JSON schema in `_HEADER` (line 22) with the expanded schema from the spec. The new schema adds: `market_context`, `equipment_context`, `condition_assessment`, `cost_considerations`, `scenario_analysis`, `marketing_guidance`, `missing_data_impact`, `key_value_drivers`, `assumptions`, `sources`, and `currency` in the valuation object.

- [ ] **Step 2: Add location-awareness instructions to _HEADER**

After the existing currency line, add instructions for location-aware market context:
- Canadian equipment → reference WCSB, Montney, Duvernay, provincial regs
- US equipment → reference Permian, Eagle Ford, Marcellus, US gas pricing
- Cross-border → transport costs, re-certification, FX friction
- When ambiguous → ask the user

- [ ] **Step 3: Add comparable analysis instructions to _REASONING**

Add to the reasoning section:
- Note ask vs. transaction value conversion (80-90%)
- Flag when comps are from same operator/location (strongest basis)
- Distinguish individual retail comps from bulk/lot sale comps
- Always include listing URL for every comparable

- [ ] **Step 4: Verify prompt builds and tests pass**

```bash
PYTHONPATH=backend python3 -c "from app.pricing_v2.prompts import build_system_prompt; p = build_system_prompt(); print(f'Length: {len(p)}')"
PYTHONPATH=backend python3 -m pytest backend/tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/prompts.py
git commit -m "feat: upgrade system prompt with richer output schema and location awareness"
```

### Task 5: Integrate normalize into service.py

**Files:**
- Modify: `backend/app/pricing_v2/service.py`

- [ ] **Step 1: Import and apply normalize_structured**

In `run_pricing()`, after extracting structured JSON from Claude's response, call `normalize_structured()` to ensure all fields have defaults.

Add at the top: `from app.pricing_v2.normalize import normalize_structured`

In the return section (around line 140), wrap: `structured = normalize_structured(structured)`

- [ ] **Step 2: Run existing tests**

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -q
```
Expected: 241+ passed (no regressions)

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/service.py
git commit -m "feat: normalize structured output in pricing service"
```

---

## Chunk 3: Report Generators (Tiers 1, 2, 3)

### Task 6: Tier 1 — One-Pager report generator

**Files:**
- Create: `backend/app/pricing_v2/report_onepager.py`
- Test: `backend/tests/test_report_onepager.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_report_onepager.py
from app.pricing_v2.report_onepager import generate_onepager

def test_generates_valid_docx():
    data = {
        "valuation": {"fmv_low": 100000, "fmv_high": 200000, "fmv_mid": 150000,
                       "confidence": "HIGH", "currency": "CAD"},
        "comparables": [],
        "assumptions": ["Condition assumed B"],
    }
    result = generate_onepager(data, user_message="Test equipment", client="Test Client")
    assert isinstance(result, bytes)
    assert len(result) > 1000  # valid docx has content
    # Check it's a valid ZIP (docx format)
    assert result[:2] == b'PK'

def test_usd_currency():
    data = {
        "valuation": {"fmv_low": 50000, "fmv_high": 80000, "fmv_mid": 65000,
                       "confidence": "MEDIUM", "currency": "USD"},
    }
    result = generate_onepager(data, user_message="US equipment")
    assert isinstance(result, bytes)
```

- [ ] **Step 2: Run test — expect fail**

- [ ] **Step 3: Implement report_onepager.py**

Build a ~80-line generator that produces:
1. Header: "FUELLED APPRAISALS | FMV Valuation Support | {client}"
2. Title: "FAIR MARKET VALUE" / "VALUATION SUPPORT DOCUMENT"
3. Equipment description from user_message
4. Valuation Summary table (category, units, FMV mid/unit, subtotal)
5. Basis of Value statement
6. Confidential footer on every page

Use helpers from `report_common.py`. Currency from `data["valuation"]["currency"]`.

- [ ] **Step 4: Run test — expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/report_onepager.py backend/tests/test_report_onepager.py
git commit -m "feat: add Tier 1 one-pager report generator"
```

### Task 7: Tier 2 — Valuation Support (PwC format)

**Files:**
- Create: `backend/app/pricing_v2/report_support.py`
- Test: `backend/tests/test_report_support.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_report_support.py
from app.pricing_v2.report_support import generate_support_report

def test_generates_valid_docx():
    data = {
        "results": [
            {
                "title": "Gas Driven Zedi Pump Skid",
                "structured": {
                    "valuation": {"fmv_low": 1500, "fmv_high": 2500, "fmv_mid": 2000,
                                  "confidence": "HIGH", "currency": "CAD"},
                    "comparables": [{"title": "Kudu 5.7L", "price": 2000, "source": "Fuelled", "url": "https://fuelled.com/62549"}],
                    "condition_assessment": "Mixed condition, 60-70% complete",
                    "key_value_drivers": ["Identical comps available", "Active market"],
                    "sources": ["Fuelled.com — listing #62549"],
                    "assumptions": ["Units not individually inspected"],
                },
                "confidence": "HIGH",
            }
        ],
        "summary": {"total": 1, "completed": 1, "total_fmv_low": 1500, "total_fmv_high": 2500},
    }
    result = generate_support_report(data["results"], data["summary"], client="PwC / Longrun")
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'

def test_multiple_items():
    results = [
        {"title": f"Item {i}", "structured": {"valuation": {"fmv_low": 1000*i, "fmv_high": 2000*i, "currency": "CAD"}}, "confidence": "MEDIUM"}
        for i in range(1, 6)
    ]
    summary = {"total": 5, "completed": 5, "total_fmv_low": 15000, "total_fmv_high": 30000}
    result = generate_support_report(results, summary)
    assert isinstance(result, bytes)
```

- [ ] **Step 2: Run test — expect fail**

- [ ] **Step 3: Implement report_support.py (~200 lines)**

Model on Harsh's PwC PDF. Sections:
1. Cover + Valuation Summary table
2. Equipment Identification table
3. Equipment Categories & Condition Detail (per-category paragraphs from `condition_assessment`)
4. Comparable Sales Evidence (comps table + Key Comparable Observations from `key_value_drivers`)
5. Offer Analysis & Key Valuation Factors (if synthesis provided)
6. Valuation Reconciliation table
7. Key Value Drivers (numbered)
8. Sources (bulleted)
9. Disclaimer footer on every page

Use `report_common.py` helpers throughout.

- [ ] **Step 4: Run test — expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/report_support.py backend/tests/test_report_support.py
git commit -m "feat: add Tier 2 valuation support report (PwC format)"
```

### Task 8: Tier 3 — Upgrade existing report.py

**Files:**
- Modify: `backend/app/pricing_v2/report.py`
- Test: `backend/tests/test_report_tier3.py`

- [ ] **Step 1: Write failing test for new sections**

```python
# backend/tests/test_report_tier3.py
from app.pricing_v2.report import generate_report

def test_report_with_market_context():
    structured = {
        "valuation": {"fmv_low": 25000, "fmv_high": 40000, "confidence": "HIGH",
                       "currency": "CAD", "rcn": 300000, "list_price": 46000, "walkaway": 21000},
        "comparables": [{"title": "Test comp", "price": 30000, "source": "Fuelled", "url": "https://fuelled.com/123", "notes": "Good condition"}],
        "risks": ["PLC obsolescence"],
        "market_context": "Strong demand in Montney",
        "equipment_context": "JGP frame is uncommon",
        "condition_assessment": "Needs overhaul",
        "cost_considerations": "Transport $8K-$15K",
        "scenario_analysis": "As-is $25K-$40K, post-overhaul $45K-$60K",
        "marketing_guidance": "Lead with low hours",
        "missing_data_impact": "No serial number",
        "key_value_drivers": ["Strong comps", "Active market"],
        "assumptions": ["Condition assumed B based on description"],
        "sources": ["Fuelled.com #123"],
    }
    result = generate_report(structured, "Full analysis text", "2019 Ariel JGK/4 800HP")
    assert isinstance(result, bytes)
    assert result[:2] == b'PK'

def test_report_usd():
    structured = {
        "valuation": {"fmv_low": 50000, "fmv_high": 80000, "confidence": "MEDIUM", "currency": "USD"},
        "comparables": [],
    }
    result = generate_report(structured, "US valuation", "2020 compressor in Texas")
    assert isinstance(result, bytes)
```

- [ ] **Step 2: Run test — expect fail (new fields not rendered)**

- [ ] **Step 3: Upgrade report.py**

Migrate to use `report_common.py` helpers. Add new sections after the existing ones:
- Market Context (renders `market_context` if present)
- Equipment Context (renders `equipment_context` if present)
- Condition Assessment (renders `condition_assessment` if present)
- Cost Considerations (renders `cost_considerations` if present)
- Scenario Analysis (renders `scenario_analysis` if present)
- Marketing Guidance (renders `marketing_guidance` if present)
- Missing Data Impact (renders `missing_data_impact` if present)
- Sources (renders `sources` list if present)
- Replace boilerplate assumptions with `assumptions` from structured data

Make `_price()` use `report_common.price_fmt()` with currency from structured data.

- [ ] **Step 4: Run all tests**

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/pricing_v2/report.py backend/tests/test_report_tier3.py
git commit -m "feat: upgrade Tier 3 report with market context, risk, scenario sections"
```

---

## Chunk 4: Batch Progress Polling & Portfolio Synthesis

### Task 9: Async batch with job tracking

**Files:**
- Modify: `backend/app/api/batch.py`
- Test: `backend/tests/test_batch_progress.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_batch_progress.py
import pytest
from unittest.mock import AsyncMock, patch

def test_batch_start_returns_job_id():
    """POST /api/price/batch/start should return a job_id."""
    from app.api.batch import _batch_jobs
    # Verify the jobs dict exists
    assert isinstance(_batch_jobs, dict)

def test_batch_status_unknown_job():
    """GET /api/price/batch/{id}/status for unknown job should 404."""
    from app.api.batch import _batch_jobs
    assert "nonexistent" not in _batch_jobs
```

- [ ] **Step 2: Run tests — expect fail**

- [ ] **Step 3: Add job tracking to batch.py**

Add to `batch.py`:
- `_batch_jobs: dict[str, dict] = {}` — in-memory job state
- `POST /batch/start` — generates UUID job_id, launches `_price_batch_async()` as background task, returns `{job_id}`
- `GET /batch/{job_id}/status` — returns `{job_id, status, completed, total, current_item, results, errors, summary}`
- `_price_batch_async(job_id, items)` — same as `_price_batch` but updates `_batch_jobs[job_id]` after each item

Keep existing synchronous endpoints for backward compatibility.

- [ ] **Step 4: Run tests — expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/batch.py backend/tests/test_batch_progress.py
git commit -m "feat: add async batch job tracking with progress polling"
```

### Task 10: Portfolio synthesis endpoint

**Files:**
- Modify: `backend/app/pricing_v2/service.py`
- Modify: `backend/app/api/batch.py`
- Test: `backend/tests/test_portfolio_synthesis.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_portfolio_synthesis.py
from app.pricing_v2.normalize import normalize_structured

def test_synthesis_input_truncation():
    """200 items should compress to under 50K tokens of structured JSON."""
    items = []
    for i in range(200):
        items.append({
            "title": f"Equipment {i}",
            "structured": normalize_structured({
                "valuation": {"fmv_low": 1000*i, "fmv_high": 2000*i, "currency": "CAD"},
                "comparables": [{"title": f"Comp {i}", "price": 1500*i}],
            }),
        })
    # Simulate the truncation that prepare_synthesis_input should do
    from app.pricing_v2.service import prepare_synthesis_input
    text = prepare_synthesis_input(items)
    # Rough token estimate: 1 token ≈ 4 chars
    assert len(text) < 200_000  # ~50K tokens
```

- [ ] **Step 2: Run test — expect fail**

- [ ] **Step 3: Implement prepare_synthesis_input and run_portfolio_synthesis**

In `service.py`, add:

```python
def prepare_synthesis_input(results: list[dict]) -> str:
    """Compress batch results for portfolio synthesis — structured JSON only."""
    import json
    items = []
    for r in results:
        s = r.get("structured", {})
        v = s.get("valuation", {})
        items.append({
            "title": r.get("title", ""),
            "fmv_low": v.get("fmv_low"),
            "fmv_high": v.get("fmv_high"),
            "confidence": v.get("confidence"),
            "currency": v.get("currency", "CAD"),
            "risks": s.get("risks", [])[:3],
            "comps_count": len(s.get("comparables", [])),
        })
    return json.dumps(items, indent=None)


async def run_portfolio_synthesis(results: list[dict], summary: dict) -> dict:
    """Generate portfolio-level analysis from batch results."""
    # ... Claude API call with portfolio synthesis prompt
    # Returns: {executive_summary, category_observations, disposition_strategy, data_quality_notes}
    pass
```

- [ ] **Step 4: Add synthesis to batch endpoint**

In `batch.py`, after `_price_batch` completes, if `portfolio_synthesis=True` (default for 10+ items), call `run_portfolio_synthesis()` and include in response.

- [ ] **Step 5: Run tests — expect pass**

- [ ] **Step 6: Commit**

```bash
git add backend/app/pricing_v2/service.py backend/app/api/batch.py backend/tests/test_portfolio_synthesis.py
git commit -m "feat: add portfolio synthesis with token-efficient input preparation"
```

---

## Chunk 5: Report API & Tier Routing

### Task 11: Update reports endpoint with tier routing

**Files:**
- Modify: `backend/app/api/reports.py`
- Test: `backend/tests/test_reports.py` (update existing)

- [ ] **Step 1: Update the generate endpoint**

Modify `POST /api/reports/generate` to accept a `tier` field (1, 2, or 3) and route to the correct generator:
- `tier: 1` → `report_onepager.generate_onepager()`
- `tier: 2` → `report_support.generate_support_report()`
- `tier: 3` → `report.generate_report()` (existing, upgraded)
- Default (no tier) → existing behavior for backward compat

- [ ] **Step 2: Update existing test**

Add tier-specific test cases to `backend/tests/test_reports.py`.

- [ ] **Step 3: Run all tests**

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -q
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/reports.py backend/tests/test_reports.py
git commit -m "feat: add tier routing to reports endpoint (1=onepager, 2=support, 3=full)"
```

### Task 12: Wire portfolio_report.py to delegate to report_support.py

**Files:**
- Modify: `backend/app/pricing_v2/portfolio_report.py`

- [ ] **Step 1: Make portfolio_report delegate to report_support**

Keep `generate_portfolio_report()` function signature for backward compat (batch.py imports it). Internally, delegate to `report_support.generate_support_report()`.

- [ ] **Step 2: Run tests**

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -q
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/pricing_v2/portfolio_report.py
git commit -m "refactor: portfolio_report delegates to report_support for Tier 2 format"
```

---

## Chunk 6: Frontend — Results Table & Report Tier Picker

### Task 13: Results table component for batch jobs

**Files:**
- Create: `frontend/nova-app/components/pricing/results-table.tsx`

- [ ] **Step 1: Create the results table component**

A table that shows batch pricing results with columns: #, Equipment, FMV Range, Confidence, Comps, View button. Summary row at bottom with totals. Each row clickable — "View" calls `onSelectItem(index)`. Back button when viewing item detail. Progress bar when `isLoading`.

Props: `{ results, summary, isLoading, progress, onSelectItem }`

- [ ] **Step 2: Verify build**

```bash
cd frontend/nova-app && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/pricing/results-table.tsx
git commit -m "feat: add results table component for batch pricing"
```

### Task 14: Update intelligence panel for batch mode

**Files:**
- Modify: `frontend/nova-app/components/pricing/intelligence-panel.tsx`

- [ ] **Step 1: Add batch mode detection**

If `lastResponse` contains a `batchResults` array (set by the batch upload flow), render `ResultsTable` instead of the single-item `ValuationCard`. When user clicks "View" on a row, show that item's detail (ValuationCard + ComparablesTable + RiskCard). Back button returns to table.

State: `selectedItemIndex: number | null` — null = show table, number = show item detail.

- [ ] **Step 2: Verify build**

```bash
cd frontend/nova-app && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/pricing/intelligence-panel.tsx
git commit -m "feat: intelligence panel supports batch results table with drill-down"
```

### Task 15: Report tier picker (export button upgrade)

**Files:**
- Modify: `frontend/nova-app/components/pricing/export-button.tsx`

- [ ] **Step 1: Replace single export with dropdown**

Replace the current single "Export Report" button with a dropdown that shows three options:
- "One-Pager (1 page)" → calls API with `tier: 1`
- "Valuation Support (5-6 pages)" → calls API with `tier: 2`
- "Full Assessment (10+ pages)" → calls API with `tier: 3`

Use a simple `useState` for dropdown open/close. Each option calls the report generate API with the appropriate tier.

- [ ] **Step 2: Verify build**

```bash
cd frontend/nova-app && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/pricing/export-button.tsx
git commit -m "feat: report tier picker — one-pager, valuation support, full assessment"
```

### Task 16: Batch upload with progress polling

**Files:**
- Modify: `frontend/nova-app/components/pricing/batch-upload.tsx`
- Modify: `frontend/nova-app/lib/api.ts`

- [ ] **Step 1: Add API functions for batch start/poll**

In `api.ts`, add:
```typescript
export async function startBatchJob(file: File) { /* POST /api/price/batch/start */ }
export async function pollBatchStatus(jobId: string) { /* GET /api/price/batch/{jobId}/status */ }
export async function generateTieredReport(tier: number, data: any) { /* POST /api/reports/generate */ }
```

- [ ] **Step 2: Update batch-upload.tsx to use polling**

Replace synchronous upload with:
1. Call `startBatchJob(file)` → get `job_id`
2. Poll `pollBatchStatus(job_id)` every 2 seconds
3. Update progress display ("Pricing item 47 of 143...")
4. When complete, pass results to intelligence panel as `batchResults`

- [ ] **Step 3: Verify build**

```bash
cd frontend/nova-app && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/nova-app/lib/api.ts frontend/nova-app/components/pricing/batch-upload.tsx
git commit -m "feat: batch upload with progress polling and tier report export"
```

---

## Chunk 7: Integration & Verification

### Task 17: Full test suite run

- [ ] **Step 1: Run all backend tests**

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/ -v
```
Expected: All tests pass (241 existing + ~15 new)

- [ ] **Step 2: Run frontend build**

```bash
cd frontend/nova-app && npm run build
```
Expected: Zero TypeScript errors, 14 routes

- [ ] **Step 3: Spot-check report output**

```bash
PYTHONPATH=backend python3 -c "
from app.pricing_v2.report_onepager import generate_onepager
from app.pricing_v2.report_support import generate_support_report
from app.pricing_v2.report import generate_report

# Tier 1
d1 = generate_onepager({'valuation': {'fmv_low': 100000, 'fmv_high': 200000, 'currency': 'USD'}}, 'Test compressor')
open('/tmp/test_tier1.docx', 'wb').write(d1)
print(f'Tier 1: {len(d1)} bytes')

# Tier 2
d2 = generate_support_report(
    [{'title': 'Test', 'structured': {'valuation': {'fmv_low': 100000, 'fmv_high': 200000, 'currency': 'CAD'}}, 'confidence': 'HIGH'}],
    {'total': 1, 'completed': 1, 'total_fmv_low': 100000, 'total_fmv_high': 200000}
)
open('/tmp/test_tier2.docx', 'wb').write(d2)
print(f'Tier 2: {len(d2)} bytes')

# Tier 3
d3 = generate_report(
    {'valuation': {'fmv_low': 25000, 'fmv_high': 40000, 'confidence': 'HIGH', 'currency': 'CAD', 'rcn': 300000},
     'comparables': [{'title': 'Comp', 'price': 30000, 'source': 'Fuelled'}],
     'market_context': 'Strong Montney demand'},
    'Full response text', 'Ariel JGK/4 800HP'
)
open('/tmp/test_tier3.docx', 'wb').write(d3)
print(f'Tier 3: {len(d3)} bytes')
print('All reports generated successfully')
"
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: portfolio assessment & report quality upgrade — complete

Implements design spec 2026-04-01-portfolio-assessment-design.md:
- Enhanced system prompt with location-aware market context
- Richer structured output schema with normalization
- Three report tiers: one-pager, valuation support (PwC), full assessment
- Async batch processing with progress polling
- Portfolio synthesis for multi-asset jobs
- Results table in intelligence panel with drill-down
- Report tier picker in export button
- Quality reference guide loaded into agent prompt"
```
