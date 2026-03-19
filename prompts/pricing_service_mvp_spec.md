# Fuelled Nova — Pricing Service MVP

## The Goal

Harsh types "What's an Ariel JGK/4 2-stage worth?" into the web app and gets the same quality answer he'd get from Cowork, backed by real data.

This is the only thing that matters right now. Everything else is later.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Web App    │     │   Cowork     │     │ Email/Batch  │
│  (Next.js)   │     │  (Desktop)   │     │  (Future)    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       │  POST /api/price   │  MCP connector      │
       └────────┬───────────┘                     │
                ▼                                  │
     ┌─────────────────────┐                      │
     │   Pricing Service   │◄─────────────────────┘
     │   (FastAPI)         │
     │                     │
     │   Claude API call   │
     │   + system prompt   │  ← SKILL.md methodology
     │   + tools           │  ← 5 Python functions
     │                     │
     └────────┬────────────┘
              │
              ▼
     ┌─────────────────────┐
     │   PostgreSQL        │
     │   - listings        │  ← 25K scraped comps
     │   - rcn_references  │  ← gold RCN anchors (sprint 1)
     │   - risk_rules      │  ← equipment risk factors
     └─────────────────────┘
```

## What to Build

### File 1: `backend/app/pricing/pricing_service.py`

This is the entire pricing brain. One file. ~300 lines.

```python
"""
Fuelled Nova Pricing Service
One Claude API call with tools. No framework. No state machine.
"""

import anthropic
from app.db.session import get_session
from sqlalchemy import text

client = anthropic.Anthropic()

# ═══════════════════════════════════════════════════════
# SYSTEM PROMPT — The methodology lives here
# ═══════════════════════════════════════════════════════

SYSTEM_PROMPT = """
You are the pricing intelligence engine for Fuelled Energy Marketing Inc.
You produce professional equipment valuations for oilfield and industrial equipment.

[METHODOLOGY]
{skill_md_content}

[RCN REFERENCE DATA]
{rcn_tables_content}

[DEPRECIATION CURVES]
{depreciation_content}

[RISK RULES]
{risk_rules_content}

[ESCALATION FACTORS]
{escalation_content}

You have access to tools that query the Fuelled marketplace database
(25,000+ equipment listings across 16 sources). Use them to find
comparable equipment and validate your RCN-based valuations.

Always show your methodology. Always flag assumptions. 
Asking prices are 80-90% of actual transaction values — note this.
Currency is CAD unless stated otherwise.
Fuelled's legal name is "Fuelled Energy Marketing Inc."
"""

# ═══════════════════════════════════════════════════════
# TOOLS — Five Python functions the agent can call
# ═══════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "search_comparables",
        "description": "Search the Fuelled marketplace database for comparable equipment listings. Returns titles, prices, locations, sources. Use this to find market evidence for valuations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Search terms to match against listing titles. E.g. ['Ariel', 'JGK', '2-stage']"
                },
                "category": {
                    "type": "string",
                    "description": "Equipment category filter. E.g. 'compressor', 'separator', 'pump', 'generator'"
                },
                "price_min": {"type": "number", "description": "Minimum price filter (CAD)"},
                "price_max": {"type": "number", "description": "Maximum price filter (CAD)"},
                "max_results": {"type": "integer", "description": "Max results to return", "default": 20}
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "get_category_stats",
        "description": "Get aggregate statistics for an equipment category in the database. Returns total listings, average/min/max price, count above thresholds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Equipment category to analyze"}
            },
            "required": ["category"]
        }
    },
    {
        "name": "lookup_rcn",
        "description": "Look up Replacement Cost New from the reference tables. Returns RCN range, scaling parameters, and confidence for a specific equipment type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment_type": {"type": "string", "description": "E.g. 'compressor', 'pump', 'separator'"},
                "manufacturer": {"type": "string", "description": "E.g. 'Ariel', 'CAT', 'Pioneer'"},
                "model": {"type": "string", "description": "E.g. 'JGK/4', '3406', 'SC10B'"},
                "drive_type": {"type": "string", "description": "gas_engine, electric_motor, gas_turbine, integral"},
                "stages": {"type": "integer", "description": "Number of stages"},
                "hp": {"type": "integer", "description": "Target horsepower for scaling"}
            },
            "required": ["equipment_type"]
        }
    },
    {
        "name": "calculate_fmv",
        "description": "Calculate Fair Market Value from RCN using depreciation factors. Returns FMV range with full factor breakdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rcn": {"type": "number", "description": "Replacement Cost New in CAD"},
                "equipment_class": {"type": "string", "description": "rotating, static, pump_jack, turbine, electrical"},
                "age_years": {"type": "integer"},
                "condition": {"type": "string", "description": "PASC rating: A, B, C, D", "default": "B"},
                "hours": {"type": "integer", "description": "Operating hours (rotating only)"},
                "service": {"type": "string", "description": "sweet, sour, sour_high_h2s", "default": "sweet"},
                "vfd_equipped": {"type": "boolean", "default": false},
                "turnkey_package": {"type": "boolean", "default": false},
                "nace_rated": {"type": "boolean", "default": false}
            },
            "required": ["rcn", "equipment_class", "age_years"]
        }
    },
    {
        "name": "check_equipment_risks",
        "description": "Check equipment-specific risk factors that affect buyer confidence and should be disclosed. Returns applicable warnings, pre-commissioning costs, and overhaul economics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equipment_type": {"type": "string"},
                "manufacturer": {"type": "string"},
                "model": {"type": "string"},
                "age_years": {"type": "integer"},
                "hours": {"type": "integer"},
                "idle_years": {"type": "integer", "description": "Years without operation"},
                "drive_type": {"type": "string"},
                "plc_model": {"type": "string", "description": "If known from drawings"},
                "location_country": {"type": "string", "description": "CA or US"},
                "identical_units": {"type": "integer", "default": 1},
                "days_on_market": {"type": "integer"},
                "total_views": {"type": "integer"}
            },
            "required": ["equipment_type", "age_years"]
        }
    }
]

# ═══════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS — Hit the real database
# ═══════════════════════════════════════════════════════

async def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a string."""
    
    if tool_name == "search_comparables":
        return await _search_comparables(tool_input)
    elif tool_name == "get_category_stats":
        return await _get_category_stats(tool_input)
    elif tool_name == "lookup_rcn":
        return await _lookup_rcn(tool_input)
    elif tool_name == "calculate_fmv":
        return _calculate_fmv(tool_input)
    elif tool_name == "check_equipment_risks":
        return _check_equipment_risks(tool_input)
    else:
        return f"Unknown tool: {tool_name}"


async def _search_comparables(params: dict) -> str:
    """Query the listings table for comparable equipment."""
    keywords = params.get("keywords", [])
    category = params.get("category", "")
    price_min = params.get("price_min", 0)
    price_max = params.get("price_max", 99999999)
    max_results = params.get("max_results", 20)
    
    # Build dynamic WHERE clause from keywords
    keyword_clauses = " OR ".join([f"title ILIKE '%{kw}%'" for kw in keywords])
    
    query = text(f"""
        SELECT title, price, currency, source_name, location, 
               year, hours, condition, url
        FROM listings
        WHERE ({keyword_clauses})
        {"AND category_normalized ILIKE :category" if category else ""}
        AND price IS NOT NULL
        AND price BETWEEN :price_min AND :price_max
        ORDER BY price DESC
        LIMIT :max_results
    """)
    
    async with get_session() as session:
        result = await session.execute(query, {
            "category": f"%{category}%" if category else None,
            "price_min": price_min,
            "price_max": price_max,
            "max_results": max_results,
        })
        rows = result.fetchall()
    
    if not rows:
        return f"No comparables found for keywords: {keywords}. This is normal for high-spec industrial equipment."
    
    output = f"Found {len(rows)} comparable listings:\n\n"
    for r in rows:
        output += f"- {r.title} | ${r.price:,.0f} {r.currency} | {r.location or 'N/A'} | {r.year or 'N/A'} | {r.source_name}\n"
    
    return output


async def _get_category_stats(params: dict) -> str:
    """Get aggregate stats for an equipment category."""
    category = params["category"]
    
    query = text("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN price IS NOT NULL THEN 1 END) as priced,
               AVG(price) as avg_price,
               MIN(price) as min_price,
               MAX(price) as max_price
        FROM listings
        WHERE category_normalized ILIKE :category
        AND price > 0
    """)
    
    async with get_session() as session:
        result = await session.execute(query, {"category": f"%{category}%"})
        row = result.fetchone()
    
    return f"Category '{category}': {row.total} total listings, {row.priced} with prices. Avg: ${row.avg_price:,.0f}, Min: ${row.min_price:,.0f}, Max: ${row.max_price:,.0f}"


async def _lookup_rcn(params: dict) -> str:
    """Look up RCN from reference tables. 
    Initially hardcoded from seed data, later from gold tables."""
    
    # TODO Sprint 2: Query rcn_price_references gold table
    # For now, the RCN data is embedded in the system prompt via rcn_reference_tables.md
    # Claude will use that context to provide RCN estimates
    
    return f"RCN lookup for {params.get('manufacturer', '')} {params.get('model', '')} — refer to reference data in system context. HP scaling: base * (target_hp / base_hp) ^ 0.6 for rotating equipment."


def _calculate_fmv(params: dict) -> str:
    """Pure math — apply depreciation factors to RCN."""
    rcn = params["rcn"]
    equipment_class = params["equipment_class"]
    age = params["age_years"]
    condition = params.get("condition", "B")
    hours = params.get("hours")
    service = params.get("service", "sweet")
    vfd = params.get("vfd_equipped", False)
    turnkey = params.get("turnkey_package", False)
    nace = params.get("nace_rated", False)
    
    # Age factor lookup
    age_curves = {
        "rotating": [(1, 0.90), (3, 0.80), (5, 0.65), (8, 0.50), (12, 0.38), (15, 0.28), (20, 0.20), (25, 0.15), (30, 0.10), (999, 0.08)],
        "static": [(1, 0.92), (3, 0.85), (5, 0.75), (8, 0.65), (12, 0.55), (15, 0.45), (20, 0.35), (25, 0.25), (30, 0.18), (999, 0.12)],
        "pump_jack": [(1, 0.92), (3, 0.85), (5, 0.78), (8, 0.70), (12, 0.60), (15, 0.50), (20, 0.40), (25, 0.30), (30, 0.22), (999, 0.15)],
        "turbine": [(1, 0.88), (3, 0.78), (5, 0.65), (8, 0.52), (12, 0.40), (15, 0.30), (20, 0.22), (25, 0.15), (30, 0.10), (999, 0.07)],
        "electrical": [(1, 0.90), (3, 0.82), (5, 0.72), (8, 0.60), (12, 0.48), (15, 0.38), (20, 0.28), (25, 0.20), (30, 0.14), (999, 0.10)],
    }
    
    curve = age_curves.get(equipment_class, age_curves["rotating"])
    age_factor = 0.08
    for max_age, factor in curve:
        if age <= max_age:
            age_factor = factor
            break
    
    # Condition factor
    condition_factors = {"A": 1.00, "B": 0.75, "C": 0.50, "D": 0.20}
    cond_factor = condition_factors.get(condition, 0.75)
    
    # Hours factor (rotating only)
    hours_factor = 1.00
    if hours is not None and equipment_class in ("rotating", "turbine"):
        if hours < 5000: hours_factor = 1.10
        elif hours < 15000: hours_factor = 1.00
        elif hours < 30000: hours_factor = 0.85
        elif hours < 50000: hours_factor = 0.70
        else: hours_factor = 0.55
    
    # Service factor
    service_factors = {"sweet": 1.00, "sour": 1.15, "sour_high_h2s": 1.25}
    svc_factor = service_factors.get(service, 1.00)
    
    # Premiums
    vfd_factor = 1.05 if vfd else 1.00
    pkg_factor = 1.05 if turnkey else 1.00
    nace_factor = 1.15 if nace else 1.00
    
    # Calculate
    combined = age_factor * cond_factor * hours_factor * svc_factor * vfd_factor * pkg_factor * nace_factor
    fmv_mid = rcn * combined
    fmv_low = fmv_mid * 0.85
    fmv_high = fmv_mid * 1.15
    
    formula = f"${rcn:,.0f} × {age_factor} (age) × {cond_factor} (condition {condition}) × {hours_factor} (hours) × {svc_factor} (service) × {vfd_factor} (VFD) × {pkg_factor} (package) × {nace_factor} (NACE) = ${fmv_mid:,.0f}"
    
    return f"FMV Calculation:\n{formula}\n\nFMV Range: ${fmv_low:,.0f} – ${fmv_mid:,.0f} – ${fmv_high:,.0f}\nRecommended list (12% premium): ${fmv_mid * 1.12:,.0f}\nWalk-away floor (92% of low): ${fmv_low * 0.92:,.0f}"


def _check_equipment_risks(params: dict) -> str:
    """Check equipment against risk rules."""
    risks = []
    age = params["age_years"]
    hours = params.get("hours")
    idle = params.get("idle_years")
    drive = params.get("drive_type", "")
    plc = params.get("plc_model", "")
    country = params.get("location_country", "CA")
    units = params.get("identical_units", 1)
    dom = params.get("days_on_market")
    views = params.get("total_views")
    mfr = params.get("manufacturer", "")
    
    # Idle equipment
    if idle and idle > 5:
        risks.append(f"IDLE EQUIPMENT: {idle} years without operation. Elastomers, seals, gaskets, and lubricants degrade with time. Pre-commissioning inspection recommended ($3K-$8K).")
    
    if idle and idle > 3 and "rotary" in params.get("equipment_type", "").lower():
        risks.append("ROTARY VANE IDLE: Carbon/graphite vanes may have absorbed moisture. Inspect before commissioning.")
    
    # PLC obsolescence
    if plc and "micrologix" in plc.lower():
        risks.append("PLC OBSOLETE: Allen-Bradley MicroLogix 1200 discontinued 2017. Budget $8K-$15K for controls upgrade.")
    elif age > 10 and drive in ("electric_motor", "gas_engine"):
        risks.append(f"CONTROLS AGE: Equipment is {age} years old. Verify PLC/controls model and support status. Budget $5K-$20K if upgrade needed.")
    
    # Cross-border
    if country == "US":
        risks.append("CROSS-BORDER: US equipment requires transport to Canada ($5K-$15K/load), potential ASME→ABSA re-registration ($2K-$5K/pressure vessel), and CAD/USD conversion.")
    
    # Volume oversupply
    if units > 10:
        risks.append(f"OVERSUPPLY: {units} identical units listed simultaneously. Per-unit pricing power significantly reduced. Recommend lot sale.")
    elif units > 3:
        risks.append(f"VOLUME: {units} identical units at same location. Buyer leverage — consider 5-10% volume discount.")
    
    # Time on market
    if dom and dom > 730 and views and views > 500:
        risks.append(f"STALE LISTING: {dom} days on market with {views:,} views and no sale. Market is saying the price is too high.")
    
    # Integral compressor
    if "ajax" in mfr.lower() or "integral" in drive:
        risks.append("INTEGRAL COMPRESSOR: Declining market preference vs. separable high-speed units. Narrower buyer pool. Apply 10-15% discount.")
    
    # Uncommon manufacturer
    uncommon = ["worthington", "energy industries", "dresser", "cooper"]
    if any(u in mfr.lower() for u in uncommon):
        risks.append(f"UNCOMMON FRAME: {mfr} parts sourcing harder than Ariel/CAT/Waukesha. Apply 5-10% discount.")
    
    if not risks:
        return "No significant risk factors identified."
    
    return "RISK FACTORS:\n" + "\n".join(f"• {r}" for r in risks)


# ═══════════════════════════════════════════════════════
# MAIN ENTRY POINT — One function the API calls
# ═══════════════════════════════════════════════════════

async def run_pricing(
    user_message: str,
    attachments: list[dict] | None = None,  # [{type: "pdf"|"image"|"csv", content: bytes}]
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    The single entry point for all pricing requests.
    
    Returns:
        {
            "response": str,           # The valuation text
            "tool_calls_made": list,   # What tools were used
            "confidence": str,         # low/medium/high
            "suggested_actions": list, # What to do next
        }
    """
    
    # Load methodology files (cached in production)
    system = _build_system_prompt()
    
    # Build messages
    messages = []
    if conversation_history:
        messages.extend(conversation_history)
    
    # Handle attachments
    content = []
    if attachments:
        for att in attachments:
            if att["type"] in ("pdf", "image"):
                content.append({
                    "type": "image" if att["type"] == "image" else "document",
                    "source": {"type": "base64", "media_type": att["media_type"], "data": att["content"]}
                })
    content.append({"type": "text", "text": user_message})
    messages.append({"role": "user", "content": content})
    
    # Call Claude with tools — loop until done
    tool_calls_made = []
    
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        
        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Process each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made.append({"tool": block.name, "input": block.input})
                    result = await handle_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            
            # Add assistant response and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        
        elif response.stop_reason == "end_turn":
            # Claude is done — extract the final text
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            
            return {
                "response": final_text,
                "tool_calls_made": tool_calls_made,
                "confidence": _assess_confidence(tool_calls_made),
                "suggested_actions": _suggest_next_steps(final_text, tool_calls_made),
            }
        
        else:
            # Unexpected stop reason
            return {
                "response": "Pricing service encountered an unexpected state.",
                "tool_calls_made": tool_calls_made,
                "confidence": "low",
                "suggested_actions": ["Retry the request"],
            }


def _build_system_prompt() -> str:
    """Load and assemble the system prompt from methodology files."""
    import os
    
    base = os.path.dirname(__file__)
    refs = os.path.join(base, "references")
    
    def read(filename):
        path = os.path.join(refs, filename)
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return ""
    
    return SYSTEM_PROMPT.format(
        skill_md_content=read("SKILL.md"),
        rcn_tables_content=read("rcn_reference_tables.md"),
        depreciation_content=read("depreciation_curves.md"),
        risk_rules_content=read("risk_rules.md"),
        escalation_content=read("escalation_factors.md"),
    )


def _assess_confidence(tool_calls: list) -> str:
    """Simple confidence assessment based on what tools were used."""
    tools_used = {tc["tool"] for tc in tool_calls}
    
    if "search_comparables" in tools_used and "calculate_fmv" in tools_used:
        return "high"  # Both RCN and comps used
    elif "calculate_fmv" in tools_used:
        return "medium"  # RCN only, no comps
    else:
        return "low"


def _suggest_next_steps(response: str, tool_calls: list) -> list:
    """Suggest what the user should do next."""
    suggestions = []
    tools_used = {tc["tool"] for tc in tool_calls}
    
    if "search_comparables" not in tools_used:
        suggestions.append("Consider running a comparable search to validate the RCN-based estimate")
    
    if "check_equipment_risks" not in tools_used:
        suggestions.append("Run a risk check for equipment-specific factors")
    
    if not suggestions:
        suggestions.append("Review the valuation and send to the client")
    
    return suggestions
```

### File 2: `backend/app/api/price.py`

The API endpoint. Thin wrapper around the service.

```python
"""
POST /api/price — Single endpoint for all pricing requests
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.pricing.pricing_service import run_pricing
import json

router = APIRouter()

@router.post("/api/price")
async def price_equipment(
    message: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """
    Accept a pricing question + optional attachments.
    Returns the valuation response.
    """
    
    # Process attachments
    attachments = []
    for f in files:
        content = await f.read()
        import base64
        attachments.append({
            "type": "pdf" if f.content_type == "application/pdf" else "image",
            "media_type": f.content_type,
            "content": base64.b64encode(content).decode(),
        })
    
    # Run the pricing service
    result = await run_pricing(
        user_message=message,
        attachments=attachments if attachments else None,
    )
    
    return result


@router.post("/api/price/stream")
async def price_equipment_stream(
    message: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """
    Streaming version — SSE events as Claude thinks.
    TODO: Implement streaming in pricing_service.
    For now, just wraps the non-streaming version.
    """
    result = await price_equipment(message, files)
    return result
```

### File 3: Reference files

Copy the methodology files into the backend:

```
backend/app/pricing/references/
├── SKILL.md                    ← Same file as Cowork uses
├── rcn_reference_tables.md     ← Same file
├── depreciation_curves.md      ← Same file
├── risk_rules.md               ← Same file
└── escalation_factors.md       ← Same file
```

One copy of truth. Both Cowork and the web app read the same files.
In production, these move to the database (the gold tables from Sprint 1).
For now, files on disk work.

## What to Strip from Nova

### Remove
- `backend/app/agents/pricing_diagnostic.py` — Replaced by pricing_service
- `backend/app/agents/pricing_llm.py` — No longer needed
- `backend/app/agents/pricing_prompts.py` — Methodology now in SKILL.md
- `backend/app/pricing/turn_classifier.py` — Claude decides what to do, not keywords
- `backend/app/agents/query_parser.py` — Same

### Keep but Don't Touch
- `backend/app/agents/pricing.py` — Keep as fallback, gate behind feature flag
- `backend/app/agents/competitive.py` — Different agent, not in scope
- `backend/app/agents/manufacturer.py` — Different agent, not in scope
- All database/scraping infrastructure — The pricing service needs it
- The Next.js frontend shell — Just needs to call `/api/price` instead of `/api/chat`

### Defer
- Token tracking / LangSmith — Table stakes, add later
- Conversation persistence — Add later
- Dashboard widgets — Nice to have, not the product
- Report generation (docx) in the web app — Phase 2, start with text responses

## The Frontend Change

Minimal. The chat component already exists. Change the API endpoint:

```javascript
// Before
const response = await fetch('/api/chat', { ... })

// After  
const response = await fetch('/api/price', { ... })
```

The response format changes from SSE streaming events to a JSON response with the valuation text. Phase 2 adds streaming back.

The only UI addition worth doing now: a file upload button so Harsh can attach PDFs (drawings, POs) to his question. The existing chat input + a file drop zone.

## Implementation Order

### Day 1: The Service
1. Create `backend/app/pricing/pricing_service.py` — the code above
2. Create `backend/app/pricing/references/` — copy the methodology files
3. Create `backend/app/api/price.py` — the endpoint
4. Wire the endpoint into FastAPI app
5. Test: `curl -X POST /api/price -F "message=What is an Ariel JGK/4 2-stage gas engine compressor worth?"` 

### Day 2: Connect the Database
1. Verify `search_comparables` hits the real listings table
2. Verify `get_category_stats` returns real numbers
3. Test with a real valuation question and check comps match what we get manually
4. Adjust SQL queries if needed

### Day 3: Frontend
1. Point the chat component at `/api/price`
2. Add file upload to the chat input
3. Test end-to-end: Harsh types question → gets valuation back
4. Verify output quality matches what we produce in this chat / Cowork

### Day 4: Consistency Check
1. Run the same valuation request through Cowork and the web app
2. Compare outputs — they should use the same methodology and reach the same numbers
3. If they diverge, the reference files are out of sync — fix
4. Document any differences and why they exist

## What This Gives You

Week 1: Harsh can type "What's a Waukesha L7044/Ariel JGK4 3-stage worth?" into the web app and get a real answer backed by 25,000 comparable listings and professional RCN data.

Week 2: Harsh can upload a P&ID and get a valuation that reads the drawing.

Week 3: The gold tables from Sprint 1 replace the flat reference files, and confidence goes up because the data is richer.

The output is the same whether it comes from Cowork, the web app, or a future email pipeline — because they all call the same service with the same methodology and the same data.

## What This Does NOT Do (Yet)
- Generate Word document reports (Cowork handles this for now)
- Streaming responses (add in Phase 2)
- Conversation memory (add in Phase 2)
- Batch processing 129 items (Cowork handles this for now)
- Email intake automation (Phase 3)

The web app starts as the "quick answer" tool. Cowork remains the "full report" tool. They converge as features are added to the service.
