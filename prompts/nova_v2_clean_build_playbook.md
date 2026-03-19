# fuelled-nova-v2 — Clean Build Playbook

## Setup

```bash
cd ~/documents/projects/fuelled-nova-v2

# Create the .env
mkdir -p backend
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql+asyncpg://fuelled:fuelled@localhost:5432/fuelled-equipment-valuation
ANTHROPIC_API_KEY=your-key-here
PRICING_V2_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
EOF

# Copy the AGENTS.md
cp /path/to/nova_v2_agent_team_prompt.md AGENTS.md

# Copy reference files
mkdir -p backend/app/pricing_v2/references
# Copy all 6 reference .md files into references/
```

## The Rules (put these in AGENTS.md preamble OR as Claude Code instructions)

Add this to the top of your AGENTS.md or set it in Claude Code config:

```
CODE QUALITY RULES — ENFORCED ON EVERY FILE:

1. NO UNNECESSARY ABSTRACTIONS. If a function is called once, inline it.
   Don't create BaseService, AbstractTool, ToolRegistry, or any pattern
   that exists "for future extensibility."

2. NO UTILS FILES. No utils.py, helpers.py, common.py, or misc.py.
   Every function lives in the file that uses it.

3. NO CLASS HIERARCHIES. Use plain functions unless state is genuinely needed.
   The tools are functions. The service is functions. The API is functions.

4. NO COMMENTED-OUT CODE. No "# TODO: implement streaming" or
   "# Uncomment for production". If it's not used, it doesn't exist.

5. NO LOGGING FRAMEWORK. Use print() for now. Add structured logging later.
   Don't install or configure logging libraries.

6. NO TYPE GYMNASTICS. Simple type hints (str, int, dict, list) are fine.
   Don't create TypedDict, Protocol, Generic, or custom type wrappers unless
   the code literally won't work without them.

7. EVERY FILE UNDER 200 LINES. If it's longer, you're doing too much.
   service.py might hit 300 — that's the one exception.

8. NO DEPENDENCY BLOAT. requirements.txt has 7 packages. Don't add more
   without explicit approval. No pydantic-settings, no structlog, no
   tenacity, no httpx (use the anthropic SDK's built-in client).

9. FLAT STRUCTURE. No nested packages deeper than app/pricing_v2/.
   No app/pricing_v2/tools/base.py. One tools.py file. One service.py file.

10. TESTS TEST REAL THINGS. No mocks of the database. No mocks of Claude.
    Tests hit the real DB (read-only) and optionally hit the real API.
    If you can't run the test without the DB, that's fine — skip it in CI.
```

## Build Phases — Run Separately, Review Between Each

### Phase 1: Skeleton + DB Connection

Open Claude Code in the project root:

```
Build Phase 1 only. Create:
1. backend/app/__init__.py
2. backend/app/config.py — load .env with python-dotenv, expose DATABASE_URL, ANTHROPIC_API_KEY, PRICING_V2_ENABLED, CORS_ORIGINS as module-level variables. No pydantic-settings. No class. Just load and export.
3. backend/app/db/__init__.py
4. backend/app/db/session.py — async SQLAlchemy engine from DATABASE_URL, get_session() async context manager, pool_size=5
5. backend/app/main.py — FastAPI app with CORS, health endpoint that tests DB connection
6. backend/requirements.txt — exactly these 7 packages: anthropic, fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, python-dotenv, python-multipart
7. backend/.gitignore

Then verify: start uvicorn, hit /api/health, confirm DB returns a listing count.

Do NOT create any other files. Do NOT create pricing_v2/ yet. Do NOT install anything not in requirements.txt.
```

**Review:** You should have 7 files. `uvicorn app.main:app` works. `/api/health` returns the listing count from the real database. If it works, move on.

### Phase 2: Tools

```
Build Phase 2 only. Create:
1. backend/app/pricing_v2/__init__.py
2. backend/app/pricing_v2/tools.py — five functions, each returns a string:
   - search_comparables(keywords, category, price_min, price_max, max_results) — queries listings table
   - get_category_stats(category) — aggregate stats for a category
   - lookup_rcn(equipment_type, manufacturer, model, drive_type, stages, hp) — returns instruction to use system context
   - calculate_fmv(rcn, equipment_class, age_years, condition, hours, service, vfd, turnkey, nace) — pure math, deterministic
   - check_equipment_risks(equipment_type, age_years, hours, idle_years, drive_type, plc_model, manufacturer, location_country, identical_units, days_on_market, total_views) — structured rule checks

Use the AGENTS.md for the exact depreciation curves, risk rules, and implementation details. Use parameterized queries for search_comparables (keywords come from LLM — sanitize).

Then test each function manually:
- search_comparables(["Ariel", "JGK"]) should return real listings
- get_category_stats("compressor") should return real counts
- calculate_fmv(1400000, "rotating", 6, "B", 12000, "sweet") should return ~$525K mid
- check_equipment_risks("compressor", 18, idle_years=17, plc_model="micrologix 1200") should return PLC + idle warnings

Do NOT create service.py yet. Do NOT create API endpoints yet. Just the tools file.
```

**Review:** One file. Five functions. Test each one by importing in a Python shell against the real database. If the math is right and the queries return data, move on.

### Phase 3: Service (The Brain)

```
Build Phase 3 only. Create:
1. backend/app/pricing_v2/prompts.py — one function: build_system_prompt() that reads all .md files from references/ directory, assembles them into the system prompt string, caches the result. Include the JSON output format instruction so Claude returns structured data the frontend can parse.

2. backend/app/pricing_v2/schemas.py — the 5 tool definitions as JSON Schema dicts for the Claude API tools parameter. Name, description, input_schema for each tool.

3. backend/app/pricing_v2/service.py — one async function: run_pricing(user_message, attachments, conversation_history) that:
   - Loads cached system prompt
   - Builds messages array
   - Calls anthropic client.messages.create() with model="claude-sonnet-4-20250514"
   - Runs the tool loop (if stop_reason=="tool_use", execute tools, append results, call again)
   - Extracts final text
   - Parses ```json blocks into structured field
   - Returns {response, structured, tools_used, confidence}

The tool loop is the core. Claude calls a tool → we execute it from tools.py → return the result → Claude continues. Loop until stop_reason=="end_turn".

Do NOT wire the API endpoint yet. Test by calling run_pricing() directly.
```

**Review:** Three files. Call `run_pricing("What's an Ariel JGK/4 2-stage worth?")` from a Python shell. Verify:
- Claude calls search_comparables (you see real database results)
- Claude calls calculate_fmv (you see the math)
- The response includes a valuation with numbers
- The structured field has parseable JSON

This is the critical review point. If the output quality matches what we've been producing in this chat, the backend is done.

### Phase 4: API Endpoint

```
Build Phase 4 only. Create:
1. backend/app/api/__init__.py
2. backend/app/api/price.py — POST /api/price endpoint. Accept message (Form field) + optional files (UploadFile list). Process attachments as base64. Call run_pricing(). Return JSON.
3. Update backend/app/main.py to mount the price router.

Test with curl:
curl -X POST http://localhost:8000/api/price \
  -F "message=What is an Ariel JGK/4 2-stage gas engine compressor worth?"
```

**Review:** The curl returns a JSON response with a valuation. That's the backend done.

### Phase 5: Tests

```
Build Phase 5. Create backend/tests/:
1. test_tools.py — test each tool function against the real database
2. test_service.py — test run_pricing with a real query (requires API key)
3. test_api.py — test the POST endpoint

These tests hit real infrastructure. No mocks. If the DB or API key isn't available, skip gracefully.
```

## After Backend: Frontend

Don't build the frontend in Claude Code. Use Stitch. The Stitch brief is ready. Once Stitch gives you the UI, drop it into `frontend/` and point it at `http://localhost:8000/api/price`.

The only frontend code Claude Code should touch is the API proxy route (if using Next.js) to avoid CORS:

```
frontend/app/api/price/route.ts — proxy POST to backend:8000/api/price
```

## File Count Target

When you're done, you should have approximately:

```
backend/
├── app/
│   ├── __init__.py              ← empty
│   ├── config.py                ← ~20 lines
│   ├── main.py                  ← ~25 lines
│   ├── api/
│   │   ├── __init__.py          ← empty
│   │   ├── price.py             ← ~40 lines
│   │   └── health.py            ← ~15 lines (or inline in main.py)
│   ├── pricing_v2/
│   │   ├── __init__.py          ← empty
│   │   ├── service.py           ← ~150-250 lines (the biggest file)
│   │   ├── tools.py             ← ~200 lines
│   │   ├── prompts.py           ← ~40 lines
│   │   ├── schemas.py           ← ~80 lines
│   │   └── references/          ← 6 markdown files (unchanged)
│   └── db/
│       ├── __init__.py          ← empty
│       └── session.py           ← ~30 lines
├── requirements.txt             ← 7 lines
└── tests/
    ├── test_tools.py            ← ~60 lines
    ├── test_service.py          ← ~40 lines
    └── test_api.py              ← ~30 lines
```

**Total Python code: ~700-800 lines across ~10 real files.**
**Total reference files: 6 markdown files (methodology).**

If Claude Code produces more than 15 Python files or more than 1,200 lines of code, something went wrong. Push back.

## Red Flags During Build

Stop and correct if you see Claude Code doing any of these:

- Creating a `base.py` or `abstract.py` or `registry.py`
- Creating a `models/` directory with SQLAlchemy ORM models (we don't need them — raw SQL is fine)
- Installing packages not in requirements.txt
- Creating a `middleware/` directory
- Adding retry logic or circuit breakers
- Creating custom exception classes
- Adding OpenTelemetry or any observability library
- Creating a Dockerfile (not yet)
- Creating alembic migrations (read-only DB!)
- Wrapping tools in a class with register/dispatch pattern
- Creating separate files for each tool

## The Stitch Brief

The Stitch brief is a separate document (nova_v2_stitch_brief_FINAL.md). Feed it to Stitch after the backend is working. The Stitch output showed:
- Dark navy gradient canvas
- Frosted glass cards with backdrop-filter
- Orange primary (#EF5D28) for CTAs and FMV highlights
- Teal secondary (#0ABAB5) for data and labels
- Warm cream text, Space Grotesk headers, JetBrains Mono for data
- ValuationCard, CompTable, RiskFactors as structured components
- Floating input bar with file attachment
- Bottom nav: Attachments, New Query, Export Report

Wire the Stitch frontend to POST /api/price. Parse the `structured` field to render ValuationCard/CompTable/RiskBadge components. Fall back to plain text for the `response` field.
