# Nova Platform — Sprint Plan

## Current State (March 21, 2026)

**Live at fuellednova.com (main branch):**
- Pricing agent working end-to-end
- HTML frontend (sidebar + chat + basic pages)
- JWT auth with 4 users
- 36,208 listings, 116 RCN references, 349 market values
- File upload, export report, feedback, JSONL logging
- Deployed on Hetzner/Coolify

**On feature branch (feature/platform-nextjs):**
- Next.js app with 45+ components
- Pricing agent mostly wired (3 minor issues to fix)
- Dashboard, Market Data, Competitive, Manufacturers pages (stubs)
- Design system ported

**Ported from V1:**
- RCN v2 engine (1,059 lines, merged to main)
- Equipment intelligence pipeline (812 lines, merged to main)

---

## Sprint 1: Production Polish (This Week — March 21-23)
**Goal: Fix the 3 issues Claude Code identified, ship quick wins**
**Branch: feature/platform-nextjs**

### Day 1 — Fix Next.js Pricing Agent (the 3 issues)
1. Chat message truncation — show full narrative with collapse, not 200 char cutoff
2. Error handling — display API errors in chat bubble
3. Methodology field — map response.response to methodology section in intelligence panel

### Day 2 — Backend Quick Wins
4. Report quality — strip markdown from .docx output, fix equipment title extraction
5. Fetch listing tool — add 6th tool to read Fuelled/competitor URLs
6. Per-user conversations (localStorage scoping — already done on main, port to Next.js)
7. Admin-only settings (role-based nav visibility — already done on main, port to Next.js)

### Day 3 — Deploy Next.js
8. Update nginx config to serve Next.js build
9. Update docker-compose for Next.js frontend
10. Deploy to fuellednova.com, replacing the HTML version
11. Smoke test all flows: login → pricing → export → feedback

---

## Sprint 2: Operations Layer (March 24-28)
**Goal: Scrapers page, AI management basics, admin foundation**
**Branch: feature/operations-pages**

### Scrapers Page
Backend endpoints:
- GET /api/admin/scrapers — list sources with status, listing count, last run, errors
- POST /api/admin/scrapers/:source/run — trigger a manual scrape
- GET /api/admin/scrapers/:source/logs — recent error logs

Frontend:
- Source table with status dots (green/yellow/red)
- Manual trigger button per source
- Last run timestamp + freshness indicator
- Error log expandable per source
- Total listings count

Data source: scrape_runs and scrape_targets tables already exist in the database.

### AI Management Page — Phase 1
Backend endpoints:
- GET /api/admin/ai/prompt — return current system prompt (read-only)
- GET /api/admin/ai/references — list loaded reference files with sizes
- GET /api/admin/ai/usage — token/cost tracking from JSONL log
- GET /api/admin/ai/tools — list registered tools with call stats from JSONL

Frontend:
- System prompt viewer (read-only, syntax highlighted)
- Reference files list with file sizes
- API usage: queries today/this week/this month, estimated cost
- Tool call statistics: which tools fire most, average per query

### Administration — Phase 1
Backend endpoints:
- GET /api/admin/users — list all users
- POST /api/admin/users — create user
- PUT /api/admin/users/:id — update role/status
- DELETE /api/admin/users/:id — deactivate user
- GET /api/admin/feedback — recent feedback with filters
- GET /api/admin/valuations — recent valuations with full detail

Frontend:
- User management table (name, email, role, last login, status)
- Add user form
- Feedback log — filterable by thumbs down, shows equipment + FMV + comment
- Valuation log — every query with tools used, confidence, structured output
- Click into a valuation to see full detail

---

## Sprint 3: Intelligence Layer (March 31 - April 4)
**Goal: Gold table management, competitive intelligence, calibration**
**Branch: feature/intelligence-layer**

### Gold Table Management
Backend endpoints:
- GET /api/admin/gold/rcn — view/search RCN references
- POST /api/admin/gold/rcn — add new RCN reference
- PUT /api/admin/gold/rcn/:id — edit existing
- GET /api/admin/gold/market — view market value references
- GET /api/admin/gold/depreciation — view depreciation observations
- GET /api/admin/gold/evidence — view staging pipeline
- POST /api/admin/gold/promote — promote staged evidence to gold

Frontend:
- RCN reference table (116 rows) — searchable, editable, add new
- Market value table (349 rows) — view only for now
- Depreciation observations (266 rows) — view only
- Evidence intake staging (772 rows) — view with promotion status
- Coverage gap analysis — categories with < 3 RCN references highlighted

### Competitive Intelligence Page
Backend endpoints:
- GET /api/competitive/new — listings added in last 7 days by source
- GET /api/competitive/stale — listings older than 1 year with no sale
- GET /api/competitive/overlap — items listed on Fuelled AND competitor
- GET /api/competitive/opportunities — below-market competitor deals (fixed query)
- GET /api/competitive/repricing — Fuelled listings below market

Frontend:
- 3 metric cards (competitor count, new this week, stale inventory)
- New listings feed by source
- Stale inventory alerts with seller info
- Below-market opportunities table (clickable)
- Fuelled repricing table (our listings that need attention)

### Calibration
- Port calibration harness from V1 (redesigned per audit)
- Map full equipment input drivers (HP, capacity, drive type, stages)
- Golden fixture tests: fixed inputs → expected outputs
- Run against 642-row appraisal dataset
- Pass/fail thresholds by category

---

## Sprint 4: Automation & Scale (April 7-11)
**Goal: Email intake, conversation persistence, MCP server**

### Email Intake
- Gmail connector watches pricing@fuelled.com
- Nova reads incoming email + attachments
- Auto-generates draft valuation
- Analyst reviews and sends
- Turnaround: days → hours

### Conversation Persistence
- Move from localStorage to conversations table in PostgreSQL
- Conversations tied to user_id
- Accessible across devices
- Searchable history

### MCP Server
- FastMCP server wrapping the 5 pricing tools
- Port 8150, streamable HTTP transport
- Claude Desktop / Cowork can query the same 36K listings
- Same tools, same data, same output as the web app

---

## Sprint 5: Client Portal & Multi-Vertical (April 14+)
**Goal: External users, expanded equipment categories**

### Client Portal
- Client login (separate from internal users)
- Submit equipment for pricing
- View their valuation history
- Request formal reports
- Self-service pricing for simple equipment

### Expanded Coverage
- Mining equipment RCN tables
- Power generation beyond O&G
- Construction equipment
- The methodology is vertical-agnostic — just needs category-specific data

---

## Branch Strategy

| Branch | Purpose | Merges To |
|---|---|---|
| main | Production — live at fuellednova.com | — |
| feature/platform-nextjs | Sprint 1 — Next.js frontend | main (end of Sprint 1) |
| feature/operations-pages | Sprint 2 — Scrapers, AI mgmt, Admin | main (end of Sprint 2) |
| feature/intelligence-layer | Sprint 3 — Gold tables, Competitive, Calibration | main (end of Sprint 3) |
| feature/automation | Sprint 4 — Email intake, MCP, conversation persistence | main (end of Sprint 4) |

One branch per sprint. Merge to main when the sprint is tested and stable. Beta testers always use main.

---

## Success Metrics

**Sprint 1:** Next.js frontend deployed, 0 broken flows
**Sprint 2:** Harsh can see scraper status, Curt can review feedback log
**Sprint 3:** Gold tables editable through UI, competitive page shows real data
**Sprint 4:** First email auto-processed, Cowork can call Nova tools
**Sprint 5:** First external client login
