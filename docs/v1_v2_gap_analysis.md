# Nova V1 → V2 Gap Analysis
**Date:** March 27, 2026
**Purpose:** Identify features/concepts from V1 (Notion spec + ruflo build) not yet captured in nova-v2 docs or code

---

## How to Read This

Each section compares a V1 feature area against what exists in nova-v2. Status codes:

- **✅ CAPTURED** — Exists in V2 docs AND code
- **📄 DOCS ONLY** — In V2 docs (feature map/punch list/stitch brief) but not built
- **⚠️ MISSING** — In V1 spec but NOT in any V2 doc or code — needs a decision
- **🚫 INTENTIONALLY DROPPED** — V1 had it, deep-code-review said SKIP, V2 deliberately excluded

---

## 1. PAGES & NAVIGATION

### V1 had 8 pages + sidebar:
| V1 Page | V2 Equivalent | Status |
|---|---|---|
| Dashboard | Dashboard (page.tsx) | ✅ CAPTURED — built + in feature map |
| Analytics (Pricing Agent) | Pricing (pricing/page.tsx) | ✅ CAPTURED — core product, 3-panel layout |
| Competitive | Competitive (competitive/page.tsx) | ✅ CAPTURED — built + in feature map |
| Manufacturers | Manufacturers (manufacturers/page.tsx) | ✅ CAPTURED — coming soon placeholder |
| **Reports** | — | ⚠️ MISSING — V1 had a full Report Builder page with templates, preview, scheduling. V2 has report.py for .docx export but no dedicated page |
| **Costs / LLM Spend** | — | ⚠️ MISSING — V1 had full costs page (daily spend chart, agent cost donut, model breakdown, budget alerts). V2 tracks cost in AI Management but no dedicated page |
| Scrapers | Scrapers (scrapers/page.tsx) | ✅ CAPTURED — built + in feature map |
| Settings/Admin | Admin (admin/page.tsx) + Settings Drawer | ✅ CAPTURED — built with users/feedback/valuations tabs |

### Additional V2 pages NOT in V1:
| V2 Page | Notes |
|---|---|
| AI Management | New in V2 — prompt viewer, reference files, usage stats, tool stats |
| Gold Tables | New in V2 — RCN/market/depreciation viewers with CRUD |
| Methodology | New in V2 — pipeline visualization, depreciation table, benchmarks |
| Market Data | Expanded in V2 beyond V1's basic market view |

### Sidebar differences:
| Feature | V1 | V2 | Status |
|---|---|---|---|
| Brand/logo | "FuelledNova" brand | "[N] Nova PLATFORM" | ✅ Different but captured |
| User profile with monogram | ✅ | User section at bottom | ✅ |
| Activity feed ("Recent" with "3 new" badge) | ✅ In V1 sidebar | — | ⚠️ MISSING |
| ⌘K command palette / global search | ✅ In V1 top bar | — | ⚠️ MISSING |
| Section labels (INTELLIGENCE, DATA) | — | ✅ In V2 stitch brief | ✅ |
| Role-gated nav (ops pages for admin/builder only) | ✅ | ✅ (admin-only settings) | ✅ |

---

## 2. PRICING AGENT

| Feature | V1 | V2 | Status |
|---|---|---|---|
| Chat interface with AI | ✅ (Narrative Loop, SSE streaming) | ✅ (chat-panel, chat-message, thinking-indicator) | ✅ CAPTURED |
| 3-panel layout (nav + chat + intelligence) | ✅ (Adaptive Dual-Pane) | ✅ In stitch brief + built | ✅ CAPTURED |
| Valuation card | ✅ | ✅ (valuation-card.tsx) | ✅ CAPTURED |
| Comparables table | ✅ | ✅ (comparables-table.tsx) | ✅ CAPTURED |
| Risk factors card | — | ✅ (risk-card.tsx) | ✅ V2 added this |
| Methodology collapse | — | ✅ (methodology-collapse.tsx) | ✅ V2 added this |
| Confidence badge | ✅ | ✅ (confidence-pill.tsx) | ✅ CAPTURED |
| File upload (PDF, images, spreadsheets) | ✅ | ✅ (file-pills.tsx, chat-input.tsx) | ✅ CAPTURED |
| Export report (.docx) | ✅ (PDF via ReportLab) | ✅ (export-button.tsx, report.py) | ✅ CAPTURED |
| Feedback thumbs up/down | ✅ | ✅ (feedback-buttons.tsx) | ✅ CAPTURED |
| Conversation sidebar/history | ✅ | ✅ (conversation-sidebar.tsx) | ✅ CAPTURED |
| SSE streaming with progressive rendering | ✅ (Custom 0:/2:/d: protocol) | REST (not SSE) | 📄 Not in V2 punch list — V2 uses synchronous response |
| **Inline charts in chat** (histogram, trend, sparkline) | ✅ (MarketChart, PriceHistogram, TrendSparkline) | — | ⚠️ MISSING — V1 rendered interactive charts inside the chat stream |
| **Agent tabs** (Pricing/Competitive/Manufacturer) | ✅ Multi-agent routing | — | ⚠️ MISSING — V1 had tabbed agents in analytics. V2 pricing-only for now |
| **Clickable citations [1][2][3] → Evidence Panel** | ✅ Full 3-tier system | — | ⚠️ MISSING — see Traceability section |
| **Batch pricing** (spreadsheet upload → batch valuation) | — | 📄 In punch list P1 | 📄 DOCS — punch list has this |
| **Portfolio report export** | — | 📄 In punch list P1 | 📄 DOCS — punch list has this |

---

## 3. TRACEABILITY & EVIDENCE PANEL

This was a major V1 concept with no equivalent in V2 docs.

| Feature | V1 | V2 | Status |
|---|---|---|---|
| **Tier 1: Inline attribution** — hover shows "Based on 23 listings, Jan-Feb 2026" | ✅ | — | ⚠️ MISSING |
| **Tier 2: Expandable summary** — methodology, data points, sources, confidence | ✅ | Partially via methodology-collapse | Partial |
| **Tier 3: Full detail modal** — comparable listings table, calculation breakdown, export | ✅ | Partially via intelligence panel | Partial |
| **Evidence Panel** (slide-out with drill-down citations) | ✅ Dedicated component + hook | — | ⚠️ MISSING |
| **Source reference schema** (source_type, source_system, confidence_score, etc.) | ✅ Formal Pydantic model | — | ⚠️ MISSING from V2 schemas |
| **Audit trail** (all AI interactions logged for compliance) | ✅ Spec'd with retention policy | JSONL logging only | ⚠️ MISSING — V2 has basic logging but not the structured audit trail |

**Decision needed:** V2's intelligence panel covers some of Tier 2-3 functionality. The question is whether the citation system ([1][2][3] → evidence panel) and formal audit trail belong in V2's roadmap or are over-engineering for current needs.

---

## 4. REPORT BUILDER

V1 had a dedicated Reports page. V2 has no equivalent page.

| Feature | V1 | V2 | Status |
|---|---|---|---|
| **Reports page** with template selection | ✅ (Reports page, "⚠️ Functional") | — | ⚠️ MISSING as a page |
| Template types: Pricing, Market, Manufacturer | ✅ Spec'd in V1 | — | ⚠️ MISSING |
| Configure parameters (equipment type, region, date range) | ✅ | — | ⚠️ MISSING |
| Real-time PDF preview | ✅ (ReportLab) | — | ⚠️ MISSING |
| Scheduled delivery (daily, weekly, monthly) | ✅ Spec'd | — | ⚠️ MISSING |
| Single-item .docx export from pricing agent | — | ✅ (export-button + report.py) | ✅ CAPTURED |
| **Portfolio/batch .docx report** (PwC format) | — | 📄 In punch list P1 | 📄 DOCS |

**Decision needed:** Is a dedicated Reports page needed, or is the export-from-pricing-agent workflow sufficient?

---

## 5. COSTS / LLM SPEND TRACKING

V1 had a full Costs page. V2 has partial coverage in AI Management.

| Feature | V1 | V2 | Status |
|---|---|---|---|
| **Dedicated Costs page** | ✅ Full page | — | ⚠️ MISSING as a standalone page |
| KPI row (Today/Month/Avg/Calls) | ✅ | In AI Management spec | 📄 DOCS |
| Daily spend area chart (7d/14d/30d) | ✅ | — | ⚠️ MISSING |
| Agent cost donut chart | ✅ | — | ⚠️ MISSING |
| Agent breakdown table | ✅ | — | ⚠️ MISSING |
| Model breakdown (Sonnet/Haiku/Embeddings) | ✅ | — | ⚠️ MISSING |
| Cost alerts / budget percentage badge | ✅ | — | ⚠️ MISSING |
| Monthly spend bar chart | ✅ | — | ⚠️ MISSING |
| Token/cost tracking from JSONL | — | 📄 In sprint plan (AI Management) | 📄 DOCS |

**Decision needed:** Fold cost tracking into AI Management page, or give it a dedicated page?

---

## 6. DESIGN SYSTEM

| Feature | V1 ("Nasturtium") | V2 ("Industrial Observatory") | Status |
|---|---|---|---|
| Dark navy canvas | ✅ | ✅ (#001628 → #000F1C) | ✅ CAPTURED |
| Glassmorphism / frosted cards | ✅ | ✅ (glass-card.tsx) | ✅ CAPTURED |
| Typography: Space Grotesk + Inter + JetBrains Mono | ✅ | ✅ (DESIGN.md + stitch brief) | ✅ CAPTURED |
| Primary orange accent | ✅ | ✅ (#EF5D28) | ✅ CAPTURED |
| Secondary teal | ✅ | ✅ (#0ABAB5) | ✅ CAPTURED |
| Confidence/status colors (green/amber/red) | ✅ | ✅ | ✅ CAPTURED |
| "No-Line" rule (no 1px dividers) | ✅ Explicit in V1 | ✅ In DESIGN.md | ✅ CAPTURED |
| Ghost borders (ultra-low opacity) | ✅ | ✅ In DESIGN.md | ✅ CAPTURED |
| **Recharts for all charts** | ✅ | — | ⚠️ MISSING — V2 has no chart library decision documented |
| **Component registry pattern** (for chat-embedded components) | ✅ (registry.ts) | — | ⚠️ MISSING |

---

## 7. BACKEND ARCHITECTURE

| Feature | V1 (LangGraph) | V2 (Direct Claude API) | Status |
|---|---|---|---|
| Agent orchestration | LangGraph (over-engineered per code review) | Direct Claude tool-use loop | 🚫 INTENTIONALLY DROPPED |
| 3 specialized agents (Pricing, Competitive, Manufacturer) | ✅ | Pricing only | V2 focused on pricing first — correct call |
| Circuit breakers (pybreaker) | ✅ | — | ⚠️ MISSING — not in V2 code or docs |
| Observability (Langfuse, GlitchTip) | ✅ (stubs) | — | 🚫 INTENTIONALLY DROPPED per code review |
| Custom SSE streaming protocol | ✅ (0:/2:/d:) | REST sync | Different approach — V2 simpler |
| Equipment intelligence pipeline | ✅ (PORT verdict) | ✅ Ported (pricing_v2/equipment/) | ✅ CAPTURED |
| RCN v2 calculator | ✅ (PORT verdict) | ✅ Ported (pricing_v2/rcn_engine/) | ✅ CAPTURED |
| Valuation engine | ✅ (REBUILD verdict) | ✅ Rebuilt (pricing_v2/service.py) | ✅ CAPTURED |
| **Competitive agent endpoints** | ✅ (api/competitive.py exists) | ✅ (api/competitive.py exists) | ✅ CAPTURED |
| **Batch pricing endpoint** | — | 📄 In punch list P1 | 📄 DOCS |
| **Rate limiting** | ✅ Spec'd | 📄 In punch list P4 | 📄 DOCS |

---

## 8. FEATURES IN V2 PUNCH LIST BUT NOT V1

These are new to V2, driven by beta testing feedback:

| Feature | Priority | Notes |
|---|---|---|
| Batch pricing engine (POST /api/price/batch) | P1 | New — clients need portfolio pricing |
| Spreadsheet upload → batch valuation | P1 | New — Mark/Harsh workflow |
| Portfolio report export (PwC format) | P1 | New — client deliverable format |
| Report template matching | P1 | New — reverse-engineer Harsh's format |
| Fetch listing tool (read URLs) | P2 | New |
| Conversation persistence in PostgreSQL | P2 | Was V1 spec but never built |
| IronHub scraper fix (Patchright) | P4 | New |
| Calibration harness | P3 | Was in V1 (REBUILD verdict) |
| MCP server for Cowork | P5 | New to V2 |
| Email intake automation | P5 | Was in V1 spec |

---

## DECISIONS (March 27, 2026)

### Added to V2 roadmap:
1. ✅ **Reports page** — Sprint 4. Template picker, parameter config, preview, batch export.
2. ✅ **Cost/LLM spend dashboard** — Folded into AI Management page (Sprint 3). KPI cards, daily spend chart, model breakdown, budget alerts.
3. ✅ **Source references in intelligence panel** — Sprint 4. Simple provenance showing which comps/gold data were used.
4. ✅ **Evidence panel (full)** — Sprint 5+. Drill-down citations from intelligence panel.
5. ✅ **Chart library: Recharts** — Documented as design decision.

### Deferred (not a priority now):
6. ⏸️ **Activity feed in sidebar** — Nice UX, but not blocking any workflow
7. ⏸️ **⌘K command palette** — Power user feature, defer
8. ⏸️ **Inline charts in chat** — Complexity not justified yet
9. ⏸️ **Multi-agent routing** — V2 is pricing-focused, other agents can come later
10. ⏸️ **Circuit breakers** — V2 is simpler by design

### Confirmed drops (per deep-code-review):
11. 🚫 LangGraph orchestration → replaced by direct Claude API ✅
12. 🚫 Observability stubs (Langfuse/GlitchTip) → deferred ✅
13. 🚫 DTO proliferation / callback soup → rebuilt simpler ✅
