# Nova Platform — Stitch UI Brief

## What This Is

An industrial equipment intelligence platform for Fuelled Energy Marketing Inc. Three core workspaces that power Fuelled's business: Pricing Intelligence, Competitive Intelligence, and Manufacturer Intelligence. Built on 36,000+ scraped equipment listings across 13 competitor sources.

## Design System (Locked — matches existing Fuelled Nova)

### Canvas
Dark navy radial gradient — #001628 center → #000F1C edges. Everything floats on this.

### Cards & Surfaces
Frosted glass. backdrop-filter: blur(12px). Semi-transparent backgrounds (rgba(255,255,255,0.04)). Subtle white hairline inset shadows for depth.

### Colors
```
Canvas: #001628 → #000F1C (radial gradient)
Surface glass: rgba(255, 255, 255, 0.04)
Surface hover: rgba(255, 255, 255, 0.07)
Borders: rgba(255, 255, 255, 0.08)

Primary (CTAs, highlights, accents): #EF5D28 (orange)
Secondary (data, links, status): #0ABAB5 (teal)

Text primary: #F2E9E1 (warm cream)
Text secondary: #A8D5CF (teal-tinted muted)
Text muted: #5A7B8F

Confidence/Status:
  High/Active: #4CAF50 (green)
  Medium/Warning: #FF9800 (amber)
  Low/Error: #F44336 (red)

Scrollbars: rgba(168, 213, 207, 0.2) — teal-tinted, nearly invisible
```

### Typography
- Headers/Display: Space Grotesk (500-700)
- Body: Inter (400-500)
- Data/Numbers/Code: JetBrains Mono (400-500)

### Motion
Subtle transitions only. prefers-reduced-motion respected. No gratuitous animation.

---

## App Structure

```
┌──────────────────────────────────────────────────────────────┐
│  Fixed Sidebar (220px)  │          Content Area              │
│                         │                                    │
│  ┌───────────────────┐  │                                    │
│  │  [N] Nova         │  │                                    │
│  │  PLATFORM         │  │                                    │
│  └───────────────────┘  │                                    │
│                         │                                    │
│  INTELLIGENCE           │                                    │
│  ● Dashboard            │                                    │
│  ● Pricing Agent        │                                    │
│  ● Competitive          │                                    │
│  ● Manufacturers        │                                    │
│                         │                                    │
│  DATA                   │                                    │
│  ● Market Data          │                                    │
│                         │                                    │
│  ─────────────────────  │                                    │
│  ● Settings       [▸]  │                                    │
│                         │                                    │
│  Fuelled Energy         │                                    │
│  Marketing Inc.         │                                    │
│  [Logout]               │                                    │
└──────────────────────────────────────────────────────────────┘
```

Sidebar: 220px fixed left, dark glass, collapsible to 48px icon strip on mobile.
Active page: orange left border (4px) + subtle bg highlight.
Section labels: tiny uppercase teal text (INTELLIGENCE, DATA).

---

## Page 1: Dashboard

The command center. Shows health of all three intelligence systems at a glance.

### Top Row — 4 Metric Cards
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ MARKET COVERAGE  │ │ PRICING HEALTH  │ │ COMPETITIVE EDGE │ │ OEM PIPELINE    │
│ 36,208          │ │ HIGH            │ │ 13 sources       │ │ —               │
│ Live listings    │ │ Last 7 days     │ │ All active       │ │ Coming soon     │
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```
Glass cards. Key number large (Space Grotesk 700). Subtitle small teal. Third card shows competitive source count with green dots.

### Recent Activity — Combined Feed
Glass card showing the last 5-8 actions across all systems:
```
TIME        TYPE                    DETAIL                              STATUS
2h ago      Pricing Valuation       Ariel JGK/4 3-Stage 1400HP         $673K-$910K  HIGH
5h ago      Pricing Valuation       VaporTech Ro-Flo VRU 40HP          $38K-$52K    MEDIUM
Yesterday   Competitor Alert        12 new Kijiji listings (compressors) View →
Yesterday   Pricing Report          Ovintiv VRU FV-2026-0314           Exported
3 days ago  Scraper Complete        36,208 total across 13 sources      ● All green
```
Each row is a link to the relevant detail. Type column has colored pills matching the system.

### Quick Actions — 3 Glass Cards at Bottom
```
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  ⊕ New Valuation      │ │  📊 Market Report     │ │  🔄 Refresh Data      │
│  Open pricing agent   │ │  Weekly intelligence  │ │  Run all scrapers     │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
```

---

## Page 2: Pricing Agent (THE CORE WORKSPACE)

Three-panel layout. This is where the work happens.

```
┌──────────┬──────────────────────────┬───────────────────────────┐
│ Sidebar  │     Chat Panel           │  Equipment Intelligence   │
│ (nav)    │     (conversation)       │  Panel (structured data)  │
│          │                          │                           │
│          │  Nova: "Welcome..."      │  ┌─ Valuation Card ────┐  │
│          │                          │  │ FMV: $673K-$910K    │  │
│          │  You: "What's a JGK/4   │  │ RCN: $2.1M          │  │
│          │  1400HP worth?"          │  │ Conf: HIGH           │  │
│          │                          │  │ Factors: ...         │  │
│          │  Nova: "Here's my       │  │ List: $886K          │  │
│          │  analysis of the..."    │  │ Walk-away: $619K     │  │
│          │                          │  └─────────────────────┘  │
│          │                          │                           │
│          │                          │  ┌─ Comparables ───────┐  │
│          │                          │  │ 4 matches found      │  │
│          │                          │  │ L5774/JGK4  $375K   │  │
│          │                          │  │ G3512/JGK4  $250K   │  │
│          │                          │  └─────────────────────┘  │
│          │                          │                           │
│          │                          │  ┌─ Risk Factors ──────┐  │
│          │                          │  │ Controls check       │  │
│          │                          │  │ Overhaul economics   │  │
│          │                          │  └─────────────────────┘  │
│          │                          │                           │
│          │                          │  ┌─ How Nova Priced ───┐  │
│          │                          │  │ ▸ View methodology   │  │
│          │                          │  └─────────────────────┘  │
│          │                          │                           │
│          │  ┌────────────────────┐  │  [Export Report]          │
│          │  │ Ask... 📎    [→]  │  │  [👍] [👎]               │
│          │  └────────────────────┘  │                           │
└──────────┴──────────────────────────┴───────────────────────────┘
```

### Chat Panel (left 55% of content area)
- Conversation history in sidebar (collapsible, localStorage)
- User messages right-aligned, glass treatment
- Nova messages left-aligned, text only (no cards in chat)
- File upload via paperclip button
- Progress messages while thinking
- Input bar fixed at bottom

### Equipment Intelligence Panel (right 45% of content area)
- Updates with each Nova response
- Components stack vertically:
  1. **Valuation Card** — FMV range (large), RCN, confidence badge, factor pills, list/walkaway
  2. **Comparables Table** — clickable rows linking to source listings
  3. **Risk Factors** — orange-tinted glass card with warnings
  4. **Methodology** — collapsible "How Nova priced this" showing the calculation
  5. **Feedback** — 👍/👎 buttons
  6. **Export Report** — downloads .docx

When no valuation has been run yet, the panel shows:
```
  ┌─────────────────────────────┐
  │                             │
  │     [Equipment icon]        │
  │                             │
  │  Ask about any equipment    │
  │  to see the intelligence    │
  │  panel populate.            │
  │                             │
  │  You can:                   │
  │  • Type a question          │
  │  • Upload a P&ID            │
  │  • Attach a client email    │
  │                             │
  └─────────────────────────────┘
```

---

## Page 3: Competitive Intelligence

Monitor competitor listings and identify opportunities.

### Top Row — 3 Metric Cards
```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ COMPETITOR DATA   │ │ NEW THIS WEEK    │ │ STALE INVENTORY  │
│ 29,564           │ │ 847              │ │ 3,210            │
│ Non-Fuelled       │ │ Across all       │ │ Listed > 1 year  │
│ listings          │ │ sources          │ │ w/ no sale       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Source Coverage Table
```
SOURCE          LISTINGS   WITH PRICE   LAST SCRAPED   STATUS   OVERLAP w/ FUELLED
bidspotter      8,220      0            15h ago        ●        12%
reflowx         7,389      5,013        16h ago        ●        8%
kijiji          5,041      3,666        15h ago        ●        22%
equipmenttrader 2,792      1,859        15h ago        ●        15%
ironplanet      2,172      1,219        16h ago        ●        11%
ironhub         2,120      0            4h ago         ●        6%
...
```
Status dots: green (<48h), yellow (2-7d), red (>7d).
"Overlap w/ Fuelled" column shows % of items that are also on fuelled.com — high overlap = sellers listing everywhere.

### Market Opportunities
Two sections (lazy-loaded):

**Below-Market Deals** — Competitor listings priced significantly below category median
```
EQUIPMENT                              CATEGORY        LISTED    MARKET AVG   DISCOUNT   SOURCE
2020 Ariel JGK/4 3-Stage Package       Compressor     $180,000   $375,000    52% below  kijiji
2018 CAT 3512 Generator Package         Generator     $120,000   $280,000    57% below  ironplanet
...
```
Each row clickable to the original listing.

**Fuelled Repricing Needed** — Our listings that appear below market
```
EQUIPMENT                              CATEGORY        OUR PRICE  MARKET AVG   GAP        ACTION
400 BBL Insulated Tank #10548           Tank           Not set    $19,000      —          Set price →
Ajax DPC-600 Compressor #10576          Compressor     Not set    $25,000      —          Set price →
...
```
Orange accent on this section. "Set price →" links to the listing editor.

### Stale Inventory Alert
```
SELLER           ITEMS LISTED > 2 YEARS   AVG VIEWS   AVG PRICE   RECOMMENDED ACTION
Ovintiv USA      129 items               1,200       $1,500      Bulk reprice → contact seller
Gran Tierra      20 items                450         $55,000     Review pricing
Discovery NR     213 items (Draft)       0           Not set     Needs pricing
```

---

## Page 4: Manufacturer Intelligence

Track OEMs and packagers for inventory acquisition.

### Status Banner
```
┌─────────────────────────────────────────────────────────────────┐
│  🏭  MANUFACTURER INTELLIGENCE — COMING SOON                    │
│                                                                 │
│  This workspace will identify and track equipment manufacturers │
│  and packagers for inventory sourcing. Currently in development.│
│                                                                 │
│  What it will do:                                               │
│  • Build manufacturer universe by equipment category            │
│  • Prioritize OEM outreach based on historical demand           │
│  • Track manufacturer relationships and inventory pipelines     │
│                                                                 │
│  [Notify me when ready]                                         │
└─────────────────────────────────────────────────────────────────┘
```

For the demo, this is a placeholder page with the description and a "coming soon" state. Clean, professional, shows the vision without faking functionality.

---

## Page 5: Market Data

Deep dive into the equipment data layer.

### Category Breakdown
```
CATEGORY             TOTAL    WITH PRICE   AVG PRICE    MIN        MAX        TREND
Compressor Package   2,141    554          $57,000      $2,000     $850,000   ↗
Separator            1,800    620          $32,000      $1,000     $275,000   →
Tank                 2,300    890          $19,000      $1,000     $72,000    →
Pump                 1,500    480          $24,000      $500       $400,000   ↗
Generator            800      310          $45,000      $3,000     $500,000   →
...
```
Trend arrow based on 30-day price direction. Teal for up, muted for flat, orange for down.

### Data Health
```
DATA SOURCE              ROWS     FRESHNESS    CONFIDENCE   STATUS
RCN Price References     116      Current      0.75 avg     ● Active
Market Value References  349      Current      0.70 avg     ● Active
Depreciation Obs.        266      Current      0.65 avg     ● Active
Evidence Intake          772      Current      Mixed        ● Active
Equipment Identities     151      Current      —            ● Active
Escalation Factors       65       Current      —            ● Active
```

### Coverage Gaps
```
⚠ EQUIPMENT CATEGORIES WITH NO RCN REFERENCE DATA:
  • OTSG / Steam Generation — 0 RCN anchors, fallback only
  • Water Treatment — 0 RCN anchors
  • Electrical Distribution — 0 RCN anchors
  
  These categories rely on Claude's general knowledge instead of gold-table data.
  Adding 3-5 RCN references per category would significantly improve accuracy.
```

---

## Settings (Slide-out Drawer, not a full page)

Triggered by the gear icon in the sidebar. Slides in from the right, 400px wide, glass treatment.

### Sections:

**API Usage**
- Queries today: 12
- Est. cost today: $18.00
- Monthly total: $247.00
- Model: claude-sonnet-4-20250514

**Data Health Summary**
- Quick version of the Market Data health table
- Red/yellow/green status for each data source

**Feedback Review**
- List of recent 👎 feedback items
- Each shows: equipment, FMV given, user comment
- Filter: show only negative feedback

**Actions**
- Export valuation log (.jsonl download)
- Clear conversation history
- Refresh market data (trigger scrapers)

---

## Responsive Behavior

- **Desktop (>1200px):** Full layout — sidebar + content. Pricing agent shows 3 panels.
- **Tablet (768-1200px):** Sidebar collapses to icons. Pricing agent: chat full width, equipment panel as a slide-over drawer.
- **Mobile (<768px):** Bottom nav instead of sidebar. Pricing agent: chat only, equipment panel accessible via tab/swipe.

---

## Demo Content

Pre-populate with real data for the demo:

**Dashboard:** Real listing counts from /api/health, recent valuations from JSONL log.
**Pricing Agent:** Welcome message + empty equipment panel waiting for input.
**Competitive:** Real source data from /api/market/sources, lazy-load opportunities.
**Market Data:** Real category stats from /api/market/categories.
**Manufacturers:** Coming soon placeholder.

---

## What This Does NOT Have
- No notification bell / alert center
- No chat with other users
- No calendar / scheduling
- No Kanban / task board
- No file browser / document manager
- No theme customization
- No onboarding wizard
- No complex role-based permissions UI
