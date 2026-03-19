# Nova V2 — System Architecture

## Design Principle

The reference files ARE the product. The pricing intelligence lives in six markdown files, not in code. The code is just plumbing that feeds those files to Claude and gives Claude tools to query the database.

```
references/           ← THE BRAIN (methodology, rules, data)
    SKILL.md
    rcn_reference_tables.md
    depreciation_curves.md
    risk_rules.md
    escalation_factors.md
    comparable_query_templates.md

service.py            ← THE PLUMBING (loads brain, calls Claude, executes tools)
tools.py              ← THE HANDS (database queries, math, risk checks)
```

Change the methodology? Edit a markdown file. Add a new risk rule? Add a line to risk_rules.md. Update an RCN anchor? Edit rcn_reference_tables.md. No code changes. No redeployment. The same files work in Cowork, the web app, and future email automation.

## Feature Flag: PRICING_V2_ENABLED

The flag controls which pricing path the app uses:

```python
# .env
PRICING_V2_ENABLED=true

# In code
if settings.PRICING_V2_ENABLED:
    # New path: Claude API + tools + reference files
    result = await pricing_v2_service.run(message, attachments)
else:
    # Old path: whatever Nova v1 was doing (fallback)
    result = await legacy_pricing.run(message)
```

This lets you:
- Deploy with the flag off (safe, nothing changes)
- Turn it on for testing
- A/B compare old vs. new output
- Roll back instantly if something breaks

## System Flow

```
User Input (text + optional files)
         │
         ▼
┌─────────────────────────┐
│  API Layer              │
│  POST /api/price        │
│                         │
│  - Parse message        │
│  - Process file uploads │
│  - Check PRICING_V2     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Pricing Service        │
│                         │
│  1. Load system prompt  │──→ references/*.md (cached on startup)
│  2. Build Claude call   │
│  3. Send to Claude API  │──→ Anthropic API (claude-sonnet-4-6)
│  4. Tool loop           │
│     └─ Claude requests  │
│        a tool call      │
│        └─ Execute tool  │──→ tools.py (DB query, math, risk check)
│        └─ Return result │
│        └─ Claude        │
│           continues     │
│  5. Return final        │
│     response            │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Response               │
│                         │
│  {                      │
│    response: "...",     │  ← Full valuation text
│    valuation: {...},    │  ← Structured FMV data (if extracted)
│    comparables: [...],  │  ← Comp listings (if found)
│    risks: [...],        │  ← Risk factors (if applicable)
│    confidence: "HIGH",  │
│    tools_used: [...]    │
│  }                      │
└─────────────────────────┘
```

## Backend File Structure

```
backend/
├── app/
│   ├── main.py                      ← FastAPI app, CORS, mount routers
│   ├── config.py                    ← Settings from .env (DB_URL, API_KEY, PRICING_V2_ENABLED)
│   │
│   ├── api/
│   │   ├── price.py                 ← POST /api/price — the one endpoint that matters
│   │   └── health.py                ← GET /api/health
│   │
│   ├── pricing_v2/                  ← Everything behind PRICING_V2_ENABLED
│   │   ├── service.py               ← The brain: loads refs, calls Claude, runs tool loop
│   │   ├── tools.py                 ← 5 tool implementations
│   │   ├── prompts.py               ← Loads + caches reference files into system prompt
│   │   ├── schemas.py               ← Tool JSON schemas for Claude API
│   │   └── references/              ← THE METHODOLOGY (same files as Cowork)
│   │       ├── SKILL.md
│   │       ├── rcn_reference_tables.md
│   │       ├── depreciation_curves.md
│   │       ├── risk_rules.md
│   │       ├── escalation_factors.md
│   │       └── comparable_query_templates.md
│   │
│   └── db/
│       └── session.py               ← Async PostgreSQL (read-only to existing Nova DB)
│
├── requirements.txt
└── tests/
    ├── test_tools.py
    ├── test_service.py
    └── test_consistency.py          ← Same question → same answer (Cowork vs web)
```

Total: ~10 files of actual code. The references folder is 6 files of methodology. That's the whole backend.

## The Five Tools

These are the only things the pricing service can DO. Everything else is Claude reasoning.

### Tool 1: `search_comparables`
**What:** Query the listings table for market evidence
**Input:** Keywords, category, price range
**Output:** List of matching listings with price, location, year, source
**Database:** `SELECT title, price, currency, source_name, location, year, hours FROM listings WHERE title ILIKE ...`

### Tool 2: `get_category_stats`
**What:** Aggregate market depth for an equipment category
**Input:** Category name
**Output:** Total count, priced count, avg/min/max price
**Database:** `SELECT COUNT(*), AVG(price), MIN(price), MAX(price) FROM listings WHERE category_normalized ILIKE ...`

### Tool 3: `lookup_rcn`
**What:** Find the replacement cost new for specific equipment
**Input:** Equipment type, manufacturer, model, drive type, stages, HP
**Output:** RCN range, scaling parameters, confidence
**Source:** Initially from reference files in system prompt. Sprint 2: from rcn_price_references gold table.

### Tool 4: `calculate_fmv`
**What:** Apply depreciation math to get Fair Market Value
**Input:** RCN, equipment class, age, condition, hours, service, premiums
**Output:** FMV range, factor breakdown, formula, list price, walk-away
**Source:** Pure deterministic math from depreciation_curves.md. No database. No LLM. Same input → same output, every time.

### Tool 5: `check_equipment_risks`
**What:** Evaluate equipment-specific risk factors
**Input:** Equipment type, age, hours, idle time, PLC model, location, volume
**Output:** List of applicable risks with cost impacts and disclosure text
**Source:** Structured rules from risk_rules.md. Deterministic checks.

## What Claude Does vs. What Code Does

| Task | Who Does It | Why |
|------|-------------|-----|
| Read a P&ID and identify components | Claude | Vision + domain knowledge |
| Decide which tools to call | Claude | Reasoning about what data is needed |
| Parse an email for client intent | Claude | Natural language understanding |
| Explain why a price is what it is | Claude | Narrative generation |
| Assess overhaul economics | Claude | Contextual reasoning |
| Identify target buyer profile | Claude | Domain reasoning |
| Query the database for comps | Code (tools.py) | Deterministic SQL |
| Calculate FMV from RCN | Code (tools.py) | Deterministic math |
| Check risk rules | Code (tools.py) | Deterministic rule matching |
| Load the methodology | Code (prompts.py) | File I/O |
| Format the API response | Code (service.py) | Serialization |

The split is clean: Claude reasons and explains, code queries and calculates. No LLM does math. No code tries to reason.

## Response Format

The API returns JSON that the frontend parses into components:

```json
{
  "response": "Full text response from Claude including methodology...",
  "structured": {
    "valuation": {
      "type": "Reciprocating Gas Compressor Package",
      "title": "Waukesha L7044GSI / Ariel JGK/4 — 3-Stage Sweet",
      "fmv_low": 320000,
      "fmv_mid": 370000,
      "fmv_high": 420000,
      "rcn": 1400000,
      "confidence": "HIGH",
      "list_price": 460000,
      "walkaway": 295000,
      "factors": [
        {"label": "Age (6yr)", "value": 0.50},
        {"label": "Condition B", "value": 0.75},
        {"label": "Hours 12K", "value": 1.00},
        {"label": "Sweet", "value": 1.00}
      ]
    },
    "comparables": [
      {"title": "L5774/JGK4 3-Stg", "price": 375000, "currency": "CAD", "location": "AB", "source": "ATB Appraisal"}
    ],
    "risks": [
      "CONTROLS AGE: Verify PLC model and firmware. Budget $5K-$20K if upgrade needed."
    ]
  },
  "tools_used": ["search_comparables", "calculate_fmv", "check_equipment_risks"],
  "confidence": "HIGH"
}
```

The `structured` field is extracted from Claude's response by prompting Claude to include structured JSON blocks. The frontend checks for `structured.valuation` → render ValuationCard. Checks for `structured.comparables` → render CompTable. Checks for `structured.risks` → render RiskBadge. Falls back to plain text if no structured data.

## How to Extract Structured Data from Claude

In the system prompt, include:

```
When you provide a valuation, include a JSON block wrapped in ```json tags 
with this structure:

{
  "valuation": { ... },
  "comparables": [ ... ],
  "risks": [ ... ]
}

The frontend will render this as structured cards. Continue with your 
narrative explanation after the JSON block.
```

The service parses the response, extracts any JSON blocks, and puts them in the `structured` field. The remaining text goes in `response`.

## Consistency Guarantee

**How Cowork and the web app produce the same output:**

1. Same reference files → Same methodology
2. Same database → Same comparables
3. Same tool logic → Same FMV math
4. Same risk rules → Same warnings

The ONLY difference is the system prompt wrapper. Cowork reads the SKILL.md directly. The web app loads it into a Claude API system prompt. The content is identical.

**Test:** Run the 5 consistency test cases. If FMV ranges differ by more than 10%, the reference files are out of sync.

## Deployment

### Local Development
```bash
# Backend
cd backend
cp .env.example .env  # Add DB_URL, ANTHROPIC_API_KEY, PRICING_V2_ENABLED=true
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (from Stitch export)
cd frontend
npm install
npm run dev  # Port 3000, proxies /api to localhost:8000
```

### Production (Hetzner/Coolify — same as Nova v1)
- Backend: Docker container, connects to existing PostgreSQL
- Frontend: Vercel or same Coolify instance
- Feature flag in environment variables
- Reference files baked into the Docker image (or mounted as volume for live updates)

## Phase Roadmap

### Phase 1: Now
- [ ] Stitch → frontend UI
- [ ] pricing_v2/service.py + tools.py (the 5 tools hitting real DB)
- [ ] POST /api/price endpoint
- [ ] Wire frontend to backend
- [ ] Consistency test: web app vs Cowork

### Phase 2: Equipment Intelligence (Sprint 1 from other workstream)
- [ ] Gold tables (rcn_price_references, market_value_references, etc.)
- [ ] lookup_rcn tool queries gold table instead of reference files
- [ ] Evidence intake from appraisal PDFs
- [ ] Escalation applied automatically

### Phase 3: Report Generation
- [ ] generate_report tool produces .docx from the web app
- [ ] Same template as Cowork reports
- [ ] Download button in the UI

### Phase 4: Email Intake
- [ ] Gmail connector watches for pricing requests
- [ ] Auto-processes, drafts response for review
- [ ] Harsh approves and sends

### Phase 5: Streaming + Polish
- [ ] Streaming responses (SSE) so Harsh sees Claude thinking
- [ ] Conversation persistence
- [ ] Tool activity indicators ("Searching 25,142 listings...")
- [ ] Mobile responsive
