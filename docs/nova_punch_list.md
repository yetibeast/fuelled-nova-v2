# Nova Platform — Punch List (Updated March 25, 2026)

## Context: What Beta Testing Revealed

Three days of beta testing surfaced a critical gap between how we built the system and how the team actually uses it:

**We built:** A chat-based pricing agent for individual equipment queries.
**They need:** A batch pricing engine that processes full client inventories and produces professional reports ready to send to PwC, ARC Resources, and other clients.

**Mark's workflow:** Receives a 213-item Discovery NR spreadsheet → needs individual pricing on every line → needs portfolio summary with lot recommendations → sends to client.

**Harsh's workflow:** Receives a 143-item Zedi/Kudu shack list → needs valuation with comparisons, factors, and sources → produces a formatted report → sends directly to PwC (Big 4 accounting firm).

Both hit the same wall: the web app can't handle batch jobs. They time out, aggregate instead of pricing individually, or produce reports that aren't client-ready.

**This changes the priority order.** The batch pricing engine and report template aren't Sprint 4 features — they're the core product. Everything else (scrapers, admin pages, gold tables) supports these two workflows.

---

## PRIORITY 1: Client-Facing Workflows (This Week)

These are blocking real revenue. Mark and Harsh are producing client deliverables today.

### Batch Pricing Engine
- [ ] POST /api/price/batch — accepts JSON array of equipment items
- [ ] Processes each item through the existing 5-tool pricing loop sequentially
- [ ] Returns array of individual valuations with structured data per item
- [ ] Timeout handling: 60s per item, skip and flag failures, don't kill the batch
- [ ] Progress callback or polling endpoint so frontend can show "Pricing item 47 of 213..."
- [ ] Queue-based if needed (BullMQ or simple async loop) for 100+ item batches

### Spreadsheet Upload → Batch Valuation
- [ ] Frontend: drag-and-drop spreadsheet upload on pricing agent page
- [ ] Backend: parse XLSX/CSV, extract columns (title, category, specs, location)
- [ ] Map parsed rows to batch pricing endpoint
- [ ] Return results as downloadable XLSX with all pricing columns added

### Portfolio Report Export
- [ ] Multi-item .docx report matching Harsh's PwC format (pending his template)
- [ ] Sections: Executive Summary, Portfolio Summary Table, Category Breakdown, Individual Line Items, Methodology, Assumptions, Disclaimer
- [ ] Category-level lot sale recommendations auto-generated
- [ ] Cross-border notes auto-included when location is US
- [ ] Professional formatting: navy headers, orange accents, alternating rows, Fuelled branding

### Report Template Matching
- [ ] Get Harsh's PwC report (the one he sent to Nicole)
- [ ] Reverse-engineer exact layout, sections, formatting
- [ ] Replace current report.py output with matched template
- [ ] Single-item and multi-item variants of same template
- [ ] Comparisons section (RCN vs Market Comp approach shown side-by-side)
- [ ] Factors section (age, condition, hours, service type multipliers shown explicitly)
- [ ] Sources section (which database comps were used, with URLs)

### Report Quality Fixes (Current report.py)
- [ ] Strip markdown artifacts from .docx output (**, ##, ---, *)
- [ ] Equipment title extraction: use structured data, not raw user message
- [ ] Executive summary: clean 2-3 sentences from structured data, no Claude narrative dump
- [ ] Fix edge case where chat message leaks into equipment description field

---

## PRIORITY 2: Pricing Agent Improvements (This Week)

Fixes that make the individual pricing workflow better for all users.

### Already Done
- [x] Chat message collapse/expand (Sprint 1)
- [x] Error display in chat (Sprint 1)
- [x] Methodology panel mapping (Sprint 1)
- [x] Per-user conversation history (Sprint 1)
- [x] Admin-only settings visibility (Sprint 1)
- [x] JWT auth with real users (deployed)

### Still Needed
- [ ] Fetch listing tool — read Fuelled/competitor URLs when pasted in chat
- [ ] Conversation memory — follow-up questions in same context
- [ ] Conversation persistence in PostgreSQL (currently localStorage)
- [ ] Nova icon replacement (orange robot → "N" badge)
- [ ] Login page stats: show real listing count from API, not hardcoded 25,104
- [ ] 3-panel layout in Next.js (nav + chat + intelligence panel) — Sprint 1 built this

---

## PRIORITY 3: Platform Pages (Next Week)

The operations layer. Sprint 2 and 3 built the frontend + backend. Testing and polish needed.

### Built — Needs End-to-End Testing
- [ ] Gold Tables: RCN add/edit/delete (frontend + backend exist, untested)
- [ ] Admin: Add User form (frontend + backend exist, untested)
- [ ] Admin: Valuation log expand detail (UI built, polish needed)
- [ ] Admin: Feedback log expand detail (UI built, polish needed)
- [ ] Competitive: Repricing table (endpoint may exist, frontend wiring unclear)

### Built — Working with Real Data
- [x] Scraper page: source listing counts
- [x] AI Management: model, prompt length, reference files, usage stats, tool stats
- [x] Admin: user table with role editing
- [x] Admin: feedback log from JSONL
- [x] Admin: valuation log from JSONL
- [x] Competitive: summary metrics, new listings, stale inventory
- [x] Gold Tables: RCN viewer (116 rows), market values, depreciation, coverage gaps
- [x] Methodology: pipeline visualization, depreciation table, benchmarks
- [x] Dashboard: all metric cards and tables working with real data

### Not Built — Stubs Only
- [ ] Manufacturers page (Coming soon placeholder)
- [ ] Market Data deep dive (basic category table may exist)
- [ ] Competitive: below-market deals, overlap analysis, weekly export

### Not Built — No Code
- [ ] Scraper management: add/remove/disable sources, manual trigger, error logs, history
- [ ] AI Management: view full system prompt, prompt version history, test changes, API key rotation, model selection
- [ ] Gold Tables: evidence intake staging (772 rows), promotion workflow
- [ ] Admin: password reset, deactivate user, session management, deployment info, error log viewer
- [ ] Calibration harness (642-row dataset, accuracy metrics by category)

---

## PRIORITY 4: Infrastructure & Deployment

### Deployment
- [ ] Next.js docker-compose serving new frontend (currently still HTML on main)
- [ ] Merge feature branches to main when ready to switch
- [ ] Update CORS_ORIGINS for Next.js frontend
- [ ] Set GitHub repo back to private
- [ ] Add JWT_SECRET to Coolify env vars (done locally, needs production)

### Reliability
- [ ] PostgreSQL automated backups on Hetzner
- [ ] Backend health monitoring / alerting (uptime check)
- [ ] Coolify database resource cleanup (red dot — cosmetic, manual container works)
- [ ] Rate limiting on pricing endpoints (prevent accidental 1000-query batch)

### Data Quality
- [ ] IronHub scraper fix (Patchright cookie persistence — diagnosed, not applied)
- [ ] Zero-price sources: bidspotter, ironhub, govdeals, allsurplus, surplusrecord, ritchiebros, energyauctions
- [ ] Category normalization gaps (NULL category_normalized on some listings)
- [ ] 3-stage compressor RCN data thin (3 entries)
- [ ] Heater/tank/separator scaling families not in RCN tables
- [ ] Calibration accuracy: compressors 28.6%, pumps 34.5%, separators 44.4% median error

---

## PRIORITY 5: Future (Sprint 4+)

- [ ] Email intake automation (Gmail watch → auto-valuation → analyst review → send)
- [ ] MCP server (port 8150) for Cowork/Claude Code integration
- [ ] Client portal (external users, self-service pricing)
- [ ] Expanded equipment categories (mining, power gen, construction)
- [ ] Weekly automated competitive reports
- [ ] AI Management: prompt A/B testing against known equipment

---

## Revised Sprint Plan

### Sprint 4 (This Week — March 25-28)
**Goal: Batch pricing and report template — the two things clients need NOW**

Day 1: Batch pricing endpoint + spreadsheet parser
Day 2: Portfolio report template (match Harsh's PwC format when received)
Day 3: Wire batch upload into Next.js frontend, end-to-end test
Day 4: Deploy to production, test with real Discovery/Zedi data

### Sprint 5 (Next Week — March 31 - April 4)
**Goal: Platform switch + polish**

- Merge Next.js to main, replace HTML frontend
- End-to-end test all Sprint 2/3 pages with real data
- Fix anything beta testers flagged
- Fetch listing tool
- Conversation persistence in DB

### Sprint 6 (April 7-11)
**Goal: Email intake + automation**

- Gmail connector watches pricing inbox
- Auto-draft valuation from incoming email + attachments
- Analyst reviews and sends
- MCP server for Cowork

---

## What We Learned

1. **The report IS the product.** Not the chat, not the dashboard — the .docx that goes to PwC. Everything else is infrastructure supporting report quality.

2. **Batch > individual.** Real workflow is "price this spreadsheet of 143 items" not "what's a separator worth." Individual pricing is for quick checks. Revenue comes from portfolio jobs.

3. **The skill package was right.** Workflow C (Portfolio Pricing) described exactly what Mark and Harsh need. We just need to wire it into the web app instead of running it through Claude Code locally.

4. **Speed matters less than completeness.** A 5-minute batch job that prices everything individually is better than a 10-second aggregate that gives one number. Users will wait for quality.
