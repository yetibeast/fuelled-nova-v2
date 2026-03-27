# Nova V2 — Final Execution Plan (March 27, 2026)

## Inputs Consolidated
- V1→V2 gap analysis (Claude Desktop review)
- Punch list v2 (beta testing feedback)
- Sprint plan (Sprints 1-3 complete)
- Session transcript (deployment, client work, real usage patterns)
- Harsh's PwC report request
- Mark's Discovery batch pricing request

---

## Current State

### Live at fuellednova.com
- JWT auth, 5 users, pricing agent with 6 tools, 36,208 listings
- File upload, export report, feedback, JSONL logging
- HTML frontend (chat-interface + basic multi-page app)
- **STATUS: App containers stopped — needs redeploy**

### On Feature Branches (not deployed)
- Sprint 1: Next.js pricing agent fixes + auth (feature/platform-nextjs)
- Sprint 2: Scrapers, AI Management, Admin (feature/operations-pages — merged to main)
- Sprint 3: Gold tables, Competitive, Methodology (feature/intelligence-layer)

### Ported from V1
- RCN v2 engine: 7 files, 1,059 lines (merged to main)
- Equipment intelligence: 7 files, 812 lines (on feature branch)

---

## Gap Analysis Decisions

### ADD to roadmap:
1. **Reports page** with template selection — Harsh needs this for PwC workflow
2. **Batch pricing endpoint** — Mark (213 items) and Harsh (143 items) both blocked
3. **Cost/LLM spend charts** — fold into AI Management with Recharts
4. **Recharts** as chart library — document the decision
5. **Activity feed in sidebar** — small UX win

### DEFER:
- Traceability/Evidence Panel, ⌘K palette, inline chat charts, multi-agent routing, circuit breakers, component registry, SSE streaming

### CONFIRMED DROPS (aligned with deep-code-review):
- LangGraph, Observability package, DTO proliferation, fake metrics

---

## Execution: 4 Phases

### PHASE A: Fix + Client Workflow (March 27-28)

**Immediate: Fix deployment**
- Restart/redeploy app containers on Hetzner
- Add health check + auto-restart to docker-compose
- Set GitHub repo back to private
- Verify fuellednova.com loads

**Batch pricing engine (P1 — blocking revenue)**
- POST /api/price/batch — array input, sequential processing
- 60s timeout per item, skip failures
- Progress tracking
- Spreadsheet upload: drag-drop XLSX → parse → batch price → download results

**Report template matching (P1 — client-facing)**
- Get Harsh's PwC report, reverse-engineer format
- Portfolio report: multi-item .docx with summary + line items
- Strip markdown from all .docx output
- Fix equipment title extraction

### PHASE B: Platform Switch (March 31 - April 4)

**Merge all branches, deploy Next.js**
- Merge feature/platform-nextjs + feature/intelligence-layer to main
- Update docker-compose for Next.js standalone
- Deploy, smoke test all 12 routes
- End-to-end test: Gold tables CRUD, Admin user management, Competitive real data

**Polish**
- Nova icon: "N" badge
- Login page: real listing count
- Fetch listing tool (read URLs)
- Loading skeletons
- Sidebar text fix

### PHASE C: Intelligence Polish (April 7-11)

**Cost tracking (gap analysis item)**
- Recharts: daily spend chart, model breakdown, budget alerts, monthly history
- Wire into AI Management page

**Conversation persistence**
- Move from localStorage to PostgreSQL conversations table
- Tied to user_id, accessible across devices

**Calibration rebuild**
- Port V1 parser, redesign input mapping (add HP, capacity, drive_type, stages)
- Golden fixture tests, 642-row dataset, pass/fail thresholds

### PHASE D: Automation (April 14-18)

**Email intake** — Gmail watch → auto-valuation → analyst review → send
**MCP server** — FastMCP on port 8150, 6 tools for Cowork/Claude Code
**Evidence flywheel** — every valuation → evidence row, every 👎 → review queue
**Reports page** — template selection, history, scheduled delivery

---

## Items from Gap Analysis NOT Covered Above

These are tracked but not scheduled:

| V1 Feature | Status | Decision |
|---|---|---|
| SSE streaming | V2 uses REST | Defer — REST works fine for single queries |
| Inline charts in chat | V1 had MarketChart, PriceHistogram | Defer — intelligence panel is better location |
| Agent tabs (Pricing/Competitive/Manufacturer) | V1 multi-agent | Defer — pricing-only until other data pipelines exist |
| Clickable citations [1][2][3] → Evidence Panel | V1 3-tier system | Defer — intelligence panel covers most of this |
| ⌘K command palette | V1 top bar | Defer — power user feature |
| Activity feed "3 new" badge | V1 sidebar | Phase B — small UX win during polish |
| Component registry pattern | V1 for chat-embedded components | Drop — over-engineering |
| Circuit breakers (pybreaker) | V1 spec'd but never wired | Drop — V2 is simpler by design |

---

## Key Insight

**The infrastructure is ahead of the workflow.**

Sprints 1-3 built 12 Next.js pages with real data. But beta testing showed the actual workflow is: "price this 213-item spreadsheet and give me a report I can send to PwC." That workflow doesn't exist in the app yet.

Phase A fixes the workflow. Phases B-D build the platform around it.

Fix the workflow first. Then ship the platform.
