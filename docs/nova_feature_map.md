# Nova Platform — Feature Map & Deliverables

## Core Product Pages

### 1. Pricing Agent (LIVE — beta testing now)
The revenue-generating page. Everything else supports this.
- [x] Chat interface with Claude tool-use loop
- [x] 5 tools: search_comparables, get_category_stats, lookup_rcn, calculate_fmv, check_equipment_risks
- [x] Valuation card rendering (FMV, RCN, confidence, factors)
- [x] Comparables table with clickable links
- [x] Risk factor advisory
- [x] File upload (PDF, images, spreadsheets, emails)
- [x] Export Report (.docx)
- [x] Feedback thumbs up/down
- [x] JSONL logging
- [x] Collapsible narrative
- [x] Progress messages while thinking
- [ ] 3-panel layout (nav + chat + equipment intelligence panel)
- [ ] Conversation persistence in database (currently localStorage)
- [ ] Follow-up questions in same context (conversation memory)
- [ ] Fetch listing tool (read Fuelled/competitor URLs)
- [ ] Report quality fixes (markdown cleanup, equipment title extraction)
- [ ] Source references in intelligence panel (show which DB comps/gold data were used)
- [ ] Evidence panel — drill into citations with full detail modal (from V1 traceability concept)

### 2. Dashboard
Command center — quick overview of all systems.
- [x] Listing count from /api/health
- [x] Recent valuations from JSONL log
- [x] Market overview bars by category
- [x] Market data coverage (source table)
- [x] Quick actions (New Valuation, Export, Refresh)
- [ ] Market opportunities (lazy-loaded, fixed query)
- [ ] Fuelled repricing suggestions
- [ ] Data health summary

### 3. Competitive Intelligence
Where Mark sees the landscape.
- [x] Source coverage table from /api/market/sources
- [ ] New listings this week count
- [ ] Stale inventory tracking (listed > 1 year)
- [ ] Below-market deals from competitors
- [ ] Fuelled repricing needed (our listings below market)
- [ ] Overlap analysis (same equipment on multiple platforms)
- [ ] Weekly competitive report export

### 4. Manufacturer Intelligence
Future state — inventory acquisition from OEMs.
- [ ] Coming soon placeholder (designed)
- [ ] Manufacturer universe by equipment category
- [ ] OEM outreach prioritization
- [ ] Relationship tracking

### 5. Market Data
Deep dive into the data layer.
- [x] Category breakdown from /api/market/categories
- [ ] Data health (gold table status, freshness, confidence)
- [ ] Coverage gaps (categories with no RCN data)
- [ ] Trend tracking (30-day price direction)

### 6. Reports (NEW — from V1 gap analysis)
Dedicated page for report generation and template management.
- [ ] Template picker (Pricing Report, Portfolio Report, Market Report)
- [ ] Parameter configuration (equipment type, region, date range, client name)
- [ ] Report preview before export
- [ ] Single-item .docx export (uses existing report.py)
- [ ] Multi-item portfolio report (PwC format — from punch list P1)
- [ ] Batch report from spreadsheet upload results
- [ ] Report history (previously generated reports)
- [ ] Scheduled delivery (daily/weekly/monthly — future)

---

## Operations Pages

### 7. Scrapers
Standalone page for scraper management.
- [ ] Source list with status (running, idle, failed, last run)
- [ ] Listing count per source
- [ ] Last scrape time with freshness indicator (green/yellow/red)
- [ ] Manual trigger to run individual scrapers
- [ ] Add new scraper source
- [ ] Remove/disable source
- [ ] Error logs per scraper
- [ ] Scrape history (runs over time, items added/removed)
- [ ] IronHub Patchright status (special case — cookie persistence)

### 8. AI Management
Everything related to the intelligence layer.

**Prompts:**
- [ ] View current system prompt (read-only for analysts, editable for admin)
- [ ] View reference files loaded (SKILL.md, depreciation curves, risk rules, etc.)
- [ ] Prompt version history (what changed, when)
- [ ] Test prompt changes against known equipment before deploying

**API Configuration:**
- [ ] Anthropic API key management (masked display, rotate)
- [ ] Model selection (sonnet vs opus, version pinning)
- [ ] Token usage tracking (per query, daily, monthly)
- [ ] Cost tracking ($X.XX per query, daily/monthly totals)
- [ ] Rate limit monitoring

**Cost & Spend Dashboard (NEW — from V1 gap analysis):**
- [ ] KPI cards: today's spend, monthly total, avg cost/query, total queries
- [ ] Daily spend area chart (7d/14d/30d toggle)
- [ ] Model breakdown (Sonnet vs Opus usage and cost)
- [ ] Tool cost attribution (which tools cost the most per query)
- [ ] Budget alert threshold (warn when daily/monthly spend exceeds limit)

**Tools:**
- [ ] View registered tools (5 current + any new)
- [ ] Tool call statistics (which tools fire most, avg response time)
- [ ] Tool output quality (how often comps are found, RCN match rate)

**Gold Tables:**
- [ ] RCN reference data viewer (116 rows — view, add, edit)
- [ ] Market value references viewer (349 rows)
- [ ] Depreciation observations viewer (266 rows)
- [ ] Evidence intake staging (772 rows — pending promotion)
- [ ] Promotion pipeline status (staged → resolved → promoted)
- [ ] Coverage gap analysis (categories with < 3 RCN references)

**Calibration:**
- [ ] Run calibration against known dataset
- [ ] View accuracy metrics (median error by category)
- [ ] Compare engine versions (before/after changes)

### 9. Administration

**Users:**
- [ ] User list (name, email, role, status, last login)
- [ ] Add/remove users
- [ ] Role management (admin, analyst)
- [ ] Password reset
- [ ] Session management (active sessions, force logout)

**System:**
- [ ] Database connection health
- [ ] Backend service status
- [ ] Deployment info (version, commit, last deploy time)
- [ ] Error log viewer (recent backend errors)

**Debugging:**
- [ ] Feedback log (all thumbs up/down with comments)
- [ ] Filter by thumbs down only (things to fix)
- [ ] Valuation log viewer (every query with tools used, confidence, structured output)
- [ ] Click into a valuation to see full tool call chain
- [ ] Side-by-side comparison (what Nova said vs what the analyst corrected)
- [ ] Export feedback/valuation data for analysis

---

## Priority Matrix (Updated March 27, 2026)

### Ship This Week (beta → production)
1. Report quality fixes (markdown, title)
2. Fetch listing tool (read URLs)
3. Per-user conversation history (localStorage scoping — done)
4. Admin-only settings (role check — done)
5. Frontend polish on current HTML pages

### Ship Next Week (platform launch)
6. Next.js frontend replacing HTML
7. 3-panel pricing agent layout
8. Dashboard with real data
9. Competitive intelligence page
10. Scraper status page
11. Basic admin (user list, feedback log)

### Sprint 3 (weeks 3-4)
12. AI management page (including cost/spend dashboard)
13. Gold table viewer/editor
14. Conversation persistence in database
15. Calibration harness
16. Email intake automation

### Sprint 4 (month 2)
17. Reports page — template picker, parameter config, preview, batch export
18. Source references in intelligence panel (simple evidence/provenance)
19. Manufacturer intelligence
20. Weekly automated reports

### Sprint 5+ (month 2-3)
21. Evidence panel — full drill-down citations from intelligence panel
22. Client portal (external users)
23. MCP server for Cowork/Claude Code integration
24. Scheduled report delivery

## Design Decisions (March 27, 2026)

- **Chart library:** Recharts (carried from V1 — works well with the design system)
- **Cost tracking:** Folded into AI Management page, not a standalone page
- **Reports page:** Dedicated page added to roadmap (Sprint 4)
- **Traceability:** Simple source references first (Sprint 4), full evidence panel later (Sprint 5+)
- **⌘K command palette:** Deferred — not a priority
- **Activity feed in sidebar:** Deferred — not a priority
- **Inline charts in chat:** Deferred — complexity not justified yet
