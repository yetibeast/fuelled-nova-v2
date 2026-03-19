# Nova V2 — Agent Team Build Prompt

## Context

You are building **fuelled-nova-v2**, a clean-room rebuild of Fuelled Energy Marketing's equipment pricing platform. The previous version (fuelled-nova, in `~/documents/projects/fuelled-nova`) has a working PostgreSQL database with 25,000+ scraped equipment listings and a Next.js frontend, but the backend is an over-engineered LangGraph/LangChain blob that produces worse results than a single Claude API call with good context.

This build keeps the database, kills the framework, and produces a clean product that Harsh Kansara (Operations Manager) can use immediately.

## The Product

**One sentence:** Harsh drops an email or types a question, gets a professional equipment valuation backed by 25,000 market comparables.

**Three interfaces, one brain:**
1. **Web app** — Harsh types a question in the browser, gets a valuation. Can attach PDFs.
2. **Cowork** (Claude Desktop) — Curt runs complex multi-document valuations from the desktop. Already working with skill files.
3. **Email** (future) — Pricing requests arrive by email, get processed automatically.

All three call the same pricing service with the same methodology and same data. Output is identical regardless of interface.

## Reference Materials

### Existing Database (READ ONLY — do not migrate or modify)
The fuelled-nova PostgreSQL database at `localhost:5432` (check `.env` in fuelled-nova for credentials) contains:
- `listings` table — 25,000+ equipment listings scraped from 16 sources
- Key columns: `title`, `price`, `currency`, `source_name`, `location`, `year`, `hours`, `condition`, `category_normalized`, `canonical_manufacturer`, `specs` (JSONB), `url`, `scraped_at`

Connect to this existing database. Do NOT create a new one. Do NOT run migrations against it.

### Methodology Files (provided in `references/`)
These files contain the complete pricing methodology. They are the system prompt for the Claude API call:
- `SKILL.md` — Full workflow, four valuation types, decision trees, formatting standards
- `rcn_reference_tables.md` — 34 valuation families, baseline replacement costs
- `depreciation_curves.md` — Age, condition, hours, service factor tables
- `risk_rules.md` — Equipment-specific risk factors (PLC obsolescence, idle degradation, overhaul economics)
- `escalation_factors.md` — Historical RCN escalation to current-year CAD
- `comparable_query_templates.md` — SQL patterns for searching the listings database

### Existing Frontend Reference
The fuelled-nova Next.js app in `~/documents/projects/fuelled-nova/frontend/` has components we can reference for patterns, but do NOT copy the frontend wholesale. Build fresh.

## Project Structure

```
fuelled-nova-v2/
├── AGENTS.md
├── README.md
├── .env                            ← DB credentials, Anthropic API key
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 ← FastAPI app
│   │   ├── config.py               ← Settings from .env
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── price.py            ← POST /api/price (main endpoint)
│   │   │   └── health.py           ← GET /api/health
│   │   ├── pricing/
│   │   │   ├── __init__.py
│   │   │   ├── service.py          ← The brain — Claude API + tools
│   │   │   ├── tools.py            ← Tool implementations (DB queries, FMV calc, risk check)
│   │   │   ├── prompts.py          ← System prompt builder from reference files
│   │   │   └── references/         ← Methodology files (same as Cowork)
│   │   │       ├── SKILL.md
│   │   │       ├── rcn_reference_tables.md
│   │   │       ├── depreciation_curves.md
│   │   │       ├── risk_rules.md
│   │   │       ├── escalation_factors.md
│   │   │       └── comparable_query_templates.md
│   │   └── db/
│   │       ├── __init__.py
│   │       └── session.py          ← Async PostgreSQL connection
│   ├── requirements.txt
│   └── tests/
│       ├── test_tools.py           ← Test each tool against real DB
│       ├── test_service.py         ← Test full pricing flow
│       └── test_api.py             ← Test the endpoint
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                ← The main (and only) page
│   │   ├── globals.css
│   │   └── api/
│   │       └── price/
│   │           └── route.ts        ← Proxy to backend /api/price
│   └── components/
│       ├── PriceChat.tsx            ← The main interaction component
│       ├── MessageBubble.tsx        ← Chat message display
│       ├── FileUpload.tsx           ← Drag-and-drop file upload
│       ├── ValuationCard.tsx        ← Structured valuation display
│       ├── CompTable.tsx            ← Comparable listings table
│       └── ConfidenceBadge.tsx      ← High/Medium/Low confidence indicator
└── seeds/
    └── rcn_price_reference_seed_v2.xlsx
```

## Build Sequence

### Phase 1: Backend Service (Day 1)

Build these files in order:

#### 1. `backend/app/config.py`
```python
# Load from .env: DATABASE_URL, ANTHROPIC_API_KEY
# DATABASE_URL points to the EXISTING fuelled-nova PostgreSQL
```

#### 2. `backend/app/db/session.py`
- Async SQLAlchemy engine connecting to existing fuelled-nova PostgreSQL
- Read-only connection — this service only queries the listings table
- Connection pooling (pool_size=5, max_overflow=10)

#### 3. `backend/app/pricing/tools.py`
Five tool implementations:

**`search_comparables(keywords, category, price_min, price_max, max_results)`**
- Query the `listings` table with ILIKE on title for each keyword
- Optional category_normalized filter
- Return formatted results: title, price, currency, location, year, hours, source, url
- Always include a count of how many listings were searched

**`get_category_stats(category)`**
- Aggregate query: COUNT, AVG(price), MIN(price), MAX(price) for a category
- Return human-readable summary

**`lookup_rcn(equipment_type, manufacturer, model, drive_type, stages, hp)`**
- For MVP: Return a message telling Claude to use the reference data in the system prompt
- Sprint 2: Query the rcn_price_references gold table once it exists

**`calculate_fmv(rcn, equipment_class, age_years, condition, hours, service, ...)`**
- Pure deterministic math — depreciation curves applied to RCN
- Return the formula, factor breakdown, FMV range, recommended list price, walk-away floor
- This is the same math regardless of interface — identical results guaranteed

**`check_equipment_risks(equipment_type, age_years, hours, idle_years, drive_type, plc_model, ...)`**
- Check against structured risk rules
- Return list of applicable risks with cost impacts and disclosure statements
- Cover: idle degradation, PLC obsolescence, cross-border, oversupply, time-on-market, uncommon frames

#### 4. `backend/app/pricing/prompts.py`
- Load all reference files from `references/` directory
- Assemble into a single system prompt
- Cache on startup (don't re-read files on every request)

#### 5. `backend/app/pricing/service.py`
- `async def run_pricing(user_message, attachments, conversation_history) -> dict`
- Build system prompt from prompts.py
- Define tool schemas (JSON Schema for each tool)
- Call Claude API (claude-sonnet-4-20250514) with system prompt + tools
- Tool-use loop: Claude calls tools → execute → return results → Claude continues
- Return: response text, tools used, confidence level, suggested next steps

#### 6. `backend/app/api/price.py`
- `POST /api/price` — Accept message + optional file uploads
- Process PDF/image attachments as base64 for Claude
- Call `run_pricing()`, return JSON response

#### 7. `backend/app/main.py`
- FastAPI app with CORS (allow frontend origin)
- Mount the price router
- Health check endpoint

#### 8. `requirements.txt`
```
anthropic>=0.45.0
fastapi>=0.115.0
uvicorn>=0.34.0
sqlalchemy>=2.0.0
asyncpg>=0.30.0
python-dotenv>=1.0.0
python-multipart>=0.0.18
```

### Phase 2: Frontend (Day 2-3)

The interface is one page. No dashboard, no sidebar navigation, no settings. One conversation with the pricing brain.

#### Design Direction

**Aesthetic: "Quiet authority"** — The interface should feel like talking to a senior appraiser who happens to have perfect recall of 25,000 equipment listings. Clean, professional, not flashy. The equipment data and valuations are the star, not the UI.

**Inspiration:** Linear's issue tracker meets a Bloomberg terminal's information density, but warmer. Dark mode default (oilfield people work early mornings and late nights). Copper accent (#C4834A) from the Arcanos palette — it reads as professional without being corporate blue.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  ◉ Nova                            fuelled.com  │  ← Minimal header
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ Welcome. I'm Nova, Fuelled's pricing      │  │
│  │ intelligence. Ask me about any oilfield   │  │
│  │ equipment and I'll give you a valuation   │  │
│  │ backed by 25,000 market comparables.      │  │
│  │                                           │  │
│  │ You can:                                  │  │
│  │ • Ask "What's an Ariel JGK/4 worth?"     │  │
│  │ • Upload a P&ID or PO for detailed spec   │  │
│  │ • Attach a client email for full analysis │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ USER ────────────────────────────────────┐  │
│  │ What's a 2020 Waukesha L7044 / Ariel     │  │
│  │ JGK/4 3-stage sweet gas compressor worth? │  │
│  │ It's in good condition, about 12,000 hrs. │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ NOVA ────────────────────────────────────┐  │
│  │                                           │  │
│  │  ┌─ VALUATION ──────────────────────┐     │  │
│  │  │ Waukesha L7044 / Ariel JGK/4    │     │  │
│  │  │ 3-Stage Sweet Gas Package        │     │  │
│  │  │                                  │     │  │
│  │  │ Fair Market Value                │     │  │
│  │  │ $320,000 — $420,000        HIGH  │     │  │
│  │  │                                  │     │  │
│  │  │ RCN: $1,400,000                  │     │  │
│  │  │ Age: 6yr (0.50) Cond: B (0.75)  │     │  │
│  │  │ Hours: 12K (1.00) Svc: Sweet     │     │  │
│  │  │ List at: $460,000                │     │  │
│  │  │ Walk-away: $295,000              │     │  │
│  │  └──────────────────────────────────┘     │  │
│  │                                           │  │
│  │  Here's how I got there...                │  │
│  │                                           │  │
│  │  [Methodology text with RCN source,       │  │
│  │   factor breakdown, comparable table,     │  │
│  │   risk factors, market context]           │  │
│  │                                           │  │
│  │  ┌─ COMPARABLES ────────────────────┐     │  │
│  │  │ 5 listings found                 │     │  │
│  │  │ L5774/JGK4 3-stg  $375K  AB     │     │  │
│  │  │ G3512/JGK4 3-stg  $250K  AB     │     │  │
│  │  │ G3512/Gemini 3-stg $240K  AB    │     │  │
│  │  │ ...                              │     │  │
│  │  └──────────────────────────────────┘     │  │
│  │                                           │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────┬───┐  │
│  │ Ask about equipment...           📎  │ → │  │  ← Input + file upload + send
│  └───────────────────────────────────────┴───┘  │
└─────────────────────────────────────────────────┘
```

#### Components

**`app/page.tsx`** — Single page. Full height. Conversation scroll area + fixed input at bottom.

**`PriceChat.tsx`** — Main component. Manages conversation state (messages array), handles send, displays messages. Scrolls to bottom on new message. Shows loading state while Claude thinks.

**`MessageBubble.tsx`** — Renders a single message. Two variants:
- User: Right-aligned, subtle background, shows attached files if any
- Nova: Left-aligned, parses the response to extract structured data (valuation cards, comp tables)

**`ValuationCard.tsx`** — Structured display of an FMV result. Extracted from the response text when it contains valuation data. Shows:
- Equipment name
- FMV range (large, prominent)
- Confidence badge
- Factor breakdown (small, expandable)
- List price + walk-away
- Collapsible methodology section

**`CompTable.tsx`** — Table of comparable listings when comps are found. Columns: Description, Price, Year, Location, Source. Clean, compact, sortable.

**`FileUpload.tsx`** — Drag-and-drop zone that appears when user drags files over the input area. Accepts PDF, PNG, JPG, XLSX, CSV, EML. Shows file names after upload. Files get sent as multipart form data to `/api/price`.

**`ConfidenceBadge.tsx`** — Small pill: green "HIGH", amber "MEDIUM", red "LOW". Derived from the service response.

#### Design Tokens (CSS Variables)
```css
:root {
  --bg-primary: #0F1419;        /* Near-black background */
  --bg-surface: #1A1F25;        /* Card/message background */
  --bg-elevated: #242A32;       /* Hover, active states */
  --text-primary: #E8E6E3;      /* Main text — warm white, not blue-white */
  --text-secondary: #8B9098;    /* Muted text */
  --text-tertiary: #5C6370;     /* Very muted */
  --accent: #C4834A;            /* Copper — Arcanos palette */
  --accent-muted: #8B6038;      /* Darker copper */
  --border: #2A3038;            /* Subtle borders */
  --success: #4CAF50;           /* Green — high confidence */
  --warning: #FF9800;           /* Amber — medium confidence */
  --danger: #F44336;            /* Red — low confidence */
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-display: 'Space Grotesk', system-ui, sans-serif;
}
```

#### Tech Stack
- Next.js 14+ (App Router)
- Tailwind CSS
- No component library — keep it custom and light
- No state management library — React state is sufficient for one page
- Fetch API for the backend call

### Phase 3: Wire Together (Day 3)

1. Frontend calls `POST /api/price` via Next.js API route (proxy to avoid CORS)
2. Backend receives message + files, calls Claude with tools, returns response
3. Frontend parses response, renders ValuationCard if valuation data detected
4. Frontend renders CompTable if comparable data detected
5. Conversation history maintained in React state, sent with each request for context

### Phase 4: Test & Consistency (Day 4)

Run the same 5 test cases through the web app AND through Cowork with the same skill files:

1. "What's an Ariel JGK/4 2-stage gas engine compressor worth? Good condition, 2019, 10,000 hours."
2. "Price a 48-inch 1440 PSI 3-phase separator, sweet service, 2015 vintage."
3. "What's a 750 BBL production tank worth?"
4. "I have a CAT G3306NA driving an Ariel JGP 2-stage. Owner says overhaul costs are too high. What's it worth as-is?"
5. "What's a 40HP Ro-Flo rotary vane VRU package worth? Built 2009, never been operated, NACE rated."

Compare the FMV ranges. They should be within 10% of each other. If they're not, the reference files are out of sync or the tool implementations differ.

## Constraints

- Do NOT touch the fuelled-nova database schema. Read-only connection.
- Do NOT import code from fuelled-nova. Reference it, don't copy it.
- Do NOT add LangChain, LangGraph, or any agent framework. Claude API + tools. That's it.
- Do NOT add authentication yet. Internal tool for now.
- Do NOT add conversation persistence yet. In-memory state is fine.
- Do NOT add token tracking, observability, or analytics yet. Ship first.
- Do NOT over-engineer. One page, one endpoint, one service, one database connection.
- The methodology files in `references/` are the source of truth. Both Cowork and this app read the same methodology. If you need to change methodology, change the files — don't hardcode logic.

## Definition of Done

Harsh opens the web app, types "What's a Waukesha L7044 / Ariel JGK/4 3-stage worth?", and gets back:
1. A valuation card with FMV range, confidence, and factor breakdown
2. A comparable listings table from the real database
3. Methodology explanation showing how the number was derived
4. Risk factors if applicable
5. Recommended list price and walk-away floor

The same question in Cowork produces the same FMV range (within 10%).

That's the product. Everything else is Phase 2.

## At the End, Report

1. Files created
2. How to start the backend (`uvicorn app.main:app`)
3. How to start the frontend (`npm run dev`)
4. How to run the tests
5. The 5 test case results
6. Any assumptions made
7. What's deferred to Phase 2
