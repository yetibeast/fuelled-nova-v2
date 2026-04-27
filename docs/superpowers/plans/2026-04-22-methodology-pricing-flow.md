# Pricing Methodology Flow + Worked Example Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the static `/methodology` page to show the pricing algorithm as a visual flow diagram (not six disconnected tiles), and add a `/methodology/example` sub-page that walks a *generalized* gas-compressor-package valuation through every stage with real numbers, so Mark can open it on a call and point a client at it.

**Architecture:** Frontend-only, static content. No backend changes, no DB changes, no new API calls. Two new presentational React components plus one new route. Example uses hard-coded illustrative numbers grounded in the real `rcn_engine` curves (compressor 10-year age factor = 0.59, condition-B = 0.85, etc.) so the figures are internally consistent.

**Tech Stack:** Next.js 16 (App Router, Turbopack) · Tailwind v4 (`@theme inline` tokens) · Material Symbols Outlined · existing `glass-card` design system. No test framework is set up in `frontend/nova-app` — verification is manual browser check against `dev`.

**Important harness note:** `frontend/nova-app/AGENTS.md` says *"This is NOT the Next.js you know... Read the relevant guide in `node_modules/next/dist/docs/` before writing any code."* Before creating the new route, confirm the `app/(app)/` route-group pattern + `"use client"` convention from existing pages (`methodology/page.tsx`, `reports/page.tsx`) still holds.

---

## File Structure

**Create:**
- `frontend/nova-app/components/methodology/pipeline-flow.tsx` — visual flow component (5 stages + arrows, replaces the six-tile grid currently inlined in `methodology/page.tsx`). Shows per-stage: inputs consumed, sources drawn from, one-line description.
- `frontend/nova-app/components/methodology/worked-example.tsx` — static walkthrough component. One generic compressor package carried stage-by-stage with visible numbers.
- `frontend/nova-app/app/(app)/methodology/example/page.tsx` — new route rendering `<WorkedExample />` with a back-link to `/methodology`.

**Modify:**
- `frontend/nova-app/app/(app)/methodology/page.tsx` — replace the inline `PIPELINE` constant + six-tile grid (lines 12–48) with `<PipelineFlow />`, and add a "See a worked example →" link that routes to `/methodology/example`. Leave `<DepreciationTable />`, `<RcnBenchmarks />`, and the risk-rules section untouched.

**Untouched (explicit non-goals):**
- `components/pricing/methodology-collapse.tsx` — per-valuation prose collapse. Unrelated to this work. Do not modify.
- Backend `pricing_v2/` — no changes. Worked-example numbers are illustrative, not fetched.
- `report.py` docx export — out of scope.

---

## Design Notes

**The five pipeline stages** (consolidated from the current six tiles — "Input Parsing" and "RCN Lookup" are merged into "Parse & RCN" since input parsing isn't a separate user-visible algorithm step):

1. **Parse & RCN Lookup** — Extract category, HP, year, condition from the description. Pull base RCN from reference tables (78 equipment families, HP/weight scaling, 2026-escalated). Sources: `rcn_reference_tables.md`, `seeds/rcn_price_reference_seed_v2.xlsx`.
2. **Age Factor** — Category-specific depreciation curve, linear-interpolated between milestone ages. Sources: `rcn_engine/depreciation.py` (10 curves). Blended with hours + condition into an *effective age*.
3. **Condition & Market Factors** — Condition tier (A–F, or inferred from hours), NACE premium, H2S aging, material, drive, WTI-linked market heat, geography. Sources: `rcn_engine/market_factors.py`, `rcn_engine/condition.py`.
4. **Comparable Triangulation** — Search the scraped listings DB for peer equipment; take the median and range. Cross-check the RCN-derived FMV against real market asks. Sources: `listings` table (31K+ rows across 13 marketplaces).
5. **FMV + Confidence** — Combine: `FMV = RCN_adj × Age × Condition × Market × Geography`. Triangulate with comp median. Produce a confidence score from 5 factors (RCN source quality, comp count, data freshness, input specificity, comp variance).

**Worked example (generalized compressor package):**

Input description: *"Natural gas compressor package — ~1,000 HP, 2016 vintage (10 years old), condition B (good working order), sweet service, Alberta."*

| Stage | What Nova does | Result |
|---|---|---|
| Parse & RCN | Category → `compressor`. Size → 1,000 HP (mid-range package). RCN base from reference table, escalated to 2026. | **RCN base: $420,000 CAD** |
| Age Factor | Compressor curve at age 10 (from `AGE_CURVES["compressor"]`, see `depreciation.py:18`). | **Age factor: 0.59** |
| Condition & Market | Condition B → 0.85. NACE: n/a. WTI ~$75: neutral market → 1.00. Geography Alberta: 1.00. | **Combined: 0.85** |
| Comparable Triangulation | 7 peer listings across Fuelled + Kijiji + Machinio, median $195K, range $170K–$235K. | **Comp median: $195K** |
| FMV + Confidence | `$420K × 0.59 × 0.85 × 1.00 × 1.00 = $211K` RCN-derived. Blended with comp median → **$203K FMV**. 5 comps + known specs + fresh data → **HIGH confidence**. | **FMV: $203,000 CAD (HIGH)** |

Every number above is internally consistent with the live engine's curves.

---

## Chunk 1: Pipeline Flow Component

### Task 1: Build `PipelineFlow` component

**Files:**
- Create: `frontend/nova-app/components/methodology/pipeline-flow.tsx`

- [ ] **Step 1: Read reference components for style/convention**

Read `frontend/nova-app/components/methodology/depreciation-table.tsx` and `frontend/nova-app/components/methodology/rcn-benchmarks.tsx` to confirm: `"use client"` header, `glass-card rounded-xl p-6 mb-6` container, `font-headline font-bold text-sm tracking-tight` for H3, `font-mono` for supporting text, `MaterialIcon` from `@/components/ui/material-icon`.

- [ ] **Step 2: Create the component**

Write `frontend/nova-app/components/methodology/pipeline-flow.tsx` with this exact content:

```tsx
"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

interface Stage {
  icon: string;
  label: string;
  inputs: string;
  sources: string;
  description: string;
}

const STAGES: Stage[] = [
  {
    icon: "search",
    label: "Parse & RCN Lookup",
    inputs: "Description, specs",
    sources: "RCN reference tables (78 families), HP/weight scaling",
    description: "Extract category, size, year, condition. Pull 2026-escalated base replacement cost.",
  },
  {
    icon: "trending_down",
    label: "Age Factor",
    inputs: "Year, hours, condition tier",
    sources: "10 category-specific depreciation curves",
    description: "Blend chronological age with hours and condition to compute an effective age, then look up the retention ratio on the curve.",
  },
  {
    icon: "tune",
    label: "Condition & Market Factors",
    inputs: "Condition, NACE, H2S, material, drive, WTI, region",
    sources: "Market factor tables, WTI feed, geography multipliers",
    description: "Stack premiums and discounts: sour-service aging, material choice, electric vs engine drive, market heat, regional demand.",
  },
  {
    icon: "compare_arrows",
    label: "Comparable Triangulation",
    inputs: "Category, size band, year band",
    sources: "31K+ scraped listings across 13 marketplaces",
    description: "Find peer equipment currently for sale, take the median and range, cross-check against the RCN-derived value.",
  },
  {
    icon: "calculate",
    label: "FMV & Confidence",
    inputs: "All of the above",
    sources: "Composite scoring across 5 signals",
    description: "FMV = RCN_adj × Age × Condition × Market × Geo, triangulated with comp median. Confidence reflects RCN quality, comp count, data freshness, input specificity, and comp variance.",
  },
];

export function PipelineFlow({ exampleHref }: { exampleHref?: string }) {
  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      <div className="flex items-start justify-between mb-4 gap-4 flex-wrap">
        <div>
          <h3 className="font-headline font-bold text-sm tracking-tight">Valuation Pipeline</h3>
          <p className="text-[11px] font-mono text-on-surface/40 mt-1">
            How a listing becomes a fair market value — five stages, each grounded in the gold tables.
          </p>
        </div>
        {exampleHref && (
          <a
            href={exampleHref}
            className="text-[11px] font-mono text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
          >
            See a worked example
            <MaterialIcon icon="arrow_forward" className="text-[14px]" />
          </a>
        )}
      </div>

      <ol className="space-y-3">
        {STAGES.map((stage, i) => (
          <li key={stage.label} className="relative">
            <div className="flex gap-4 items-start p-4 rounded-lg bg-surface-container-lowest border border-white/[0.04]">
              <div className="flex flex-col items-center shrink-0">
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <MaterialIcon icon={stage.icon} className="text-[18px] text-primary" />
                </div>
                <div className="text-[9px] font-mono text-on-surface/30 mt-1">Step {i + 1}</div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-mono text-on-surface font-medium mb-1">{stage.label}</div>
                <p className="text-[11px] font-mono text-on-surface/60 leading-relaxed mb-2">
                  {stage.description}
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
                  <div>
                    <span className="text-on-surface/30">Inputs: </span>
                    <span className="text-on-surface/70">{stage.inputs}</span>
                  </div>
                  <div>
                    <span className="text-on-surface/30">Sources: </span>
                    <span className="text-on-surface/70">{stage.sources}</span>
                  </div>
                </div>
              </div>
            </div>
            {i < STAGES.length - 1 && (
              <div className="flex justify-start pl-[26px] py-1" aria-hidden="true">
                <MaterialIcon icon="arrow_downward" className="text-[16px] text-on-surface/20" />
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/methodology/pipeline-flow.tsx
git commit -m "feat(methodology): add PipelineFlow component — 5-stage visual flow"
```

---

### Task 2: Wire `PipelineFlow` into `/methodology` page

**Files:**
- Modify: `frontend/nova-app/app/(app)/methodology/page.tsx` (lines 1–91)

- [ ] **Step 1: Replace the `PIPELINE` constant + six-tile grid with `<PipelineFlow />`**

In `frontend/nova-app/app/(app)/methodology/page.tsx`:

1. Remove the `PIPELINE` constant (current lines 12–19).
2. Remove the "Pipeline" JSX block (current lines 35–48 — the `<div className="glass-card rounded-xl p-6 mb-6">` containing the grid).
3. Add `import { PipelineFlow } from "@/components/methodology/pipeline-flow";` next to the other methodology imports at the top.
4. Insert `<PipelineFlow exampleHref="/methodology/example" />` in place of the removed block, above `<DepreciationTable />`.

The `MaterialIcon` import is still used by the risk-rules section lower down — leave it.

- [ ] **Step 2: Verify the page renders**

Start the dev server if it isn't running:

```bash
cd frontend/nova-app && npm run dev
```

Navigate to `http://localhost:3000/methodology` in a browser. Verify:
- The five-stage flow renders with arrows between stages.
- Each stage shows inputs + sources as two columns (or stacked on mobile).
- The "See a worked example →" link is visible in the top-right of the flow card.
- Depreciation table, RCN benchmarks, and risk rules all still render below.

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/app/(app)/methodology/page.tsx
git commit -m "feat(methodology): replace 6-tile grid with PipelineFlow + example link"
```

---

## Chunk 2: Worked Example

### Task 3: Build `WorkedExample` component

**Files:**
- Create: `frontend/nova-app/components/methodology/worked-example.tsx`

- [ ] **Step 1: Create the component**

Write `frontend/nova-app/components/methodology/worked-example.tsx` with this exact content:

```tsx
"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

const INPUT = {
  description: "Natural gas compressor package — ~1,000 HP, 2016 vintage (10 years old), condition B (good working order), sweet service, Alberta.",
  parsed: [
    { label: "Category", value: "compressor_package" },
    { label: "Horsepower", value: "1,000 HP" },
    { label: "Year", value: "2016 (age 10)" },
    { label: "Condition", value: "B — good working order" },
    { label: "Service", value: "Sweet (no H2S)" },
    { label: "Region", value: "Alberta, CA" },
  ],
};

const STAGES = [
  {
    num: 1,
    icon: "search",
    title: "Parse & RCN Lookup",
    narrative:
      "The description is parsed into structured fields. Nova matches the equipment to a reference family in the RCN table and pulls the base replacement cost, scaled for the ~1,000 HP package size and escalated from the reference year to 2026.",
    calculations: [
      { label: "RCN family matched", value: "Gas compressor package, 750–1,250 HP" },
      { label: "Base RCN (2026 CAD)", value: "$420,000" },
      { label: "Scaling factor (HP)", value: "1.00 (mid-band)" },
    ],
    output: { label: "RCN base", value: "$420,000" },
  },
  {
    num: 2,
    icon: "trending_down",
    title: "Age Factor",
    narrative:
      "For compressors, Nova uses the compressor depreciation curve with milestone ages at 0, 1, 3, 5, 7, 10, 15, 20, 25, 30, 35 years. At year 10 the retention ratio is 0.59. No hours were provided, so effective age equals chronological age.",
    calculations: [
      { label: "Curve", value: "compressor (rcn_engine/depreciation.py)" },
      { label: "Chronological age", value: "10 years" },
      { label: "Effective age", value: "10 years (no hours adjustment)" },
      { label: "Retention at year 10", value: "0.59" },
    ],
    output: { label: "Age factor", value: "× 0.59" },
  },
  {
    num: 3,
    icon: "tune",
    title: "Condition & Market Factors",
    narrative:
      "Condition B maps to 0.85. Sweet service → no H2S aging penalty. WTI is ~$75/bbl (neutral band) → no market-heat premium. Alberta geography is the baseline → 1.00.",
    calculations: [
      { label: "Condition B", value: "× 0.85" },
      { label: "H2S exposure", value: "× 1.00 (sweet)" },
      { label: "Market heat (WTI ~$75)", value: "× 1.00" },
      { label: "Geography (AB)", value: "× 1.00" },
      { label: "NACE / material / drive", value: "× 1.00 (standard)" },
    ],
    output: { label: "Combined factor", value: "× 0.85" },
  },
  {
    num: 4,
    icon: "compare_arrows",
    title: "Comparable Triangulation",
    narrative:
      "Nova queries the listings database for peer gas compressor packages in the 750–1,250 HP band, 2013–2019 vintage. Seven comparable listings surface across Fuelled, Kijiji, and Machinio. The asking-price median is $195K, range $170K–$235K. (Asking prices run 80–90% of actual transaction prices, so this is a conservative cross-check.)",
    calculations: [
      { label: "Comparable count", value: "7 listings" },
      { label: "Source spread", value: "Fuelled (3), Kijiji (2), Machinio (2)" },
      { label: "Median asking", value: "$195,000" },
      { label: "Range", value: "$170,000 – $235,000" },
    ],
    output: { label: "Comp median", value: "$195,000" },
  },
  {
    num: 5,
    icon: "calculate",
    title: "FMV & Confidence",
    narrative:
      "The RCN-derived figure and the comp median are triangulated. RCN_adj × Age × Condition × Market × Geo = $420K × 0.59 × 0.85 × 1.00 × 1.00 = $211K. Blending with the $195K comp median produces the final FMV. Confidence is HIGH: seven comps, known condition, known size, fresh data, low variance.",
    calculations: [
      { label: "RCN-derived FMV", value: "$420K × 0.59 × 0.85 = $211K" },
      { label: "Comp-median cross-check", value: "$195K" },
      { label: "Blended FMV", value: "$203,000" },
      { label: "Suggested list (× 1.12)", value: "$227,000" },
      { label: "Walk-away floor (× 0.90)", value: "$183,000" },
    ],
    output: { label: "FMV", value: "$203,000 CAD · HIGH" },
  },
];

export function WorkedExample() {
  return (
    <>
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-1">Input</h3>
        <p className="text-[11px] font-mono text-on-surface/40 mb-4">
          The listing Nova receives from the user or the scraper
        </p>
        <p className="text-sm text-on-surface/80 leading-relaxed mb-4 italic">
          &ldquo;{INPUT.description}&rdquo;
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {INPUT.parsed.map((p) => (
            <div key={p.label} className="p-3 rounded-lg bg-surface-container-lowest border border-white/[0.04]">
              <div className="text-[10px] font-mono text-on-surface/30 mb-1">{p.label}</div>
              <div className="text-xs font-mono text-on-surface">{p.value}</div>
            </div>
          ))}
        </div>
      </div>

      <ol className="space-y-4 mb-6">
        {STAGES.map((stage) => (
          <li key={stage.num} className="glass-card rounded-xl p-6">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <MaterialIcon icon={stage.icon} className="text-[20px] text-primary" />
              </div>
              <div className="flex-1">
                <div className="text-[10px] font-mono text-on-surface/30 mb-1">Stage {stage.num}</div>
                <h4 className="font-headline font-bold text-sm tracking-tight text-on-surface">{stage.title}</h4>
              </div>
            </div>

            <p className="text-xs font-mono text-on-surface/60 leading-relaxed mb-4">
              {stage.narrative}
            </p>

            <div className="space-y-1 mb-4">
              {stage.calculations.map((c, i) => (
                <div key={i} className="flex justify-between items-baseline text-[11px] font-mono py-1 border-b border-white/[0.04] last:border-b-0">
                  <span className="text-on-surface/50">{c.label}</span>
                  <span className="text-on-surface/90">{c.value}</span>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-baseline p-3 rounded-lg bg-primary/10 border border-primary/20">
              <span className="text-[11px] font-mono text-on-surface/70">{stage.output.label}</span>
              <span className="text-sm font-mono font-bold text-primary">{stage.output.value}</span>
            </div>
          </li>
        ))}
      </ol>

      <div className="glass-card rounded-xl p-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-1">Final Output</h3>
        <p className="text-[11px] font-mono text-on-surface/40 mb-4">
          What Nova returns to the user
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-surface-container-lowest border border-white/[0.04]">
            <div className="text-[10px] font-mono text-on-surface/30 mb-1">Fair Market Value</div>
            <div className="text-lg font-mono font-bold text-primary">$203,000</div>
            <div className="text-[10px] font-mono text-on-surface/40">CAD</div>
          </div>
          <div className="p-4 rounded-lg bg-surface-container-lowest border border-white/[0.04]">
            <div className="text-[10px] font-mono text-on-surface/30 mb-1">Suggested List</div>
            <div className="text-lg font-mono font-bold text-on-surface">$227,000</div>
            <div className="text-[10px] font-mono text-on-surface/40">FMV × 1.12</div>
          </div>
          <div className="p-4 rounded-lg bg-surface-container-lowest border border-white/[0.04]">
            <div className="text-[10px] font-mono text-on-surface/30 mb-1">Confidence</div>
            <div className="text-lg font-mono font-bold text-emerald-400">HIGH</div>
            <div className="text-[10px] font-mono text-on-surface/40">7 comps, known specs, fresh data</div>
          </div>
        </div>
        <p className="text-[10px] font-mono text-on-surface/30 mt-4 leading-relaxed">
          Illustrative example. Numbers are representative of the live engine (compressor 10-year age factor 0.59, condition-B 0.85) but this specific listing is synthetic.
        </p>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/nova-app/components/methodology/worked-example.tsx
git commit -m "feat(methodology): add WorkedExample component — generic compressor walkthrough"
```

---

### Task 4: Create `/methodology/example` route

**Files:**
- Create: `frontend/nova-app/app/(app)/methodology/example/page.tsx`

- [ ] **Step 1: Create the route**

Write `frontend/nova-app/app/(app)/methodology/example/page.tsx` with this exact content:

```tsx
"use client";

import Link from "next/link";
import { MaterialIcon } from "@/components/ui/material-icon";
import { WorkedExample } from "@/components/methodology/worked-example";

export default function MethodologyExamplePage() {
  return (
    <>
      <div className="mb-6">
        <Link
          href="/methodology"
          className="text-[11px] font-mono text-on-surface/40 hover:text-on-surface/70 flex items-center gap-1 mb-3 transition-colors w-fit"
        >
          <MaterialIcon icon="arrow_back" className="text-[14px]" />
          Back to methodology
        </Link>
        <h1 className="font-headline font-bold text-xl tracking-tight">Worked Example</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          A generalized compressor package carried through every stage of the pipeline
        </p>
      </div>

      <WorkedExample />
    </>
  );
}
```

- [ ] **Step 2: Verify the page renders**

With dev server running:
- Navigate to `http://localhost:3000/methodology` and click "See a worked example →".
- URL should now be `/methodology/example`.
- Page should show: back-link, heading, input card with parsed fields, 5 numbered stage cards each with narrative + calculations + highlighted output, final output card with FMV/List/Confidence, and the disclaimer footer.
- Click the back-link; should return to `/methodology`.

- [ ] **Step 3: Build check**

```bash
cd frontend/nova-app && npm run build
```
Expected: build succeeds with 0 TypeScript errors. New `/methodology/example` route appears in the route list.

- [ ] **Step 4: Commit**

```bash
git add frontend/nova-app/app/(app)/methodology/example/page.tsx
git commit -m "feat(methodology): add /methodology/example worked-example route"
```

---

## Verification Checklist (run at the end)

With dev server running, visit both pages and confirm:

- [ ] `/methodology` shows the 5-stage vertical flow with connecting arrows, each stage has icon + step number + description + inputs + sources.
- [ ] "See a worked example →" link is visible top-right of the pipeline card.
- [ ] Depreciation table, RCN benchmarks, and risk rules sections render unchanged below the flow.
- [ ] Clicking the example link navigates to `/methodology/example`.
- [ ] Example page: back-link works, input card renders description + 6 parsed fields, 5 stage cards each show narrative + calculation breakdown + highlighted output pill, final output card shows FMV $203K / List $227K / HIGH confidence, disclaimer at bottom notes numbers are illustrative.
- [ ] Mobile width (resize browser to ~400px): flow stages stack cleanly, calculation rows wrap without horizontal scroll, final output 3-col grid collapses to 1 column.
- [ ] No console errors in the browser dev tools.
- [ ] `npm run build` succeeds with 0 TypeScript errors.

---

## Out of Scope (explicit non-goals)

- Per-valuation live reasoning trace capture (discussed earlier as a separate feature — not this plan).
- Backend changes to `pricing_v2/service.py`, `tools.py`, or prompts.
- Docx report updates (`report.py`).
- New backend endpoints.
- Test framework setup for `frontend/nova-app`.
- Replacing the hard-coded numbers with a live calculation — the user asked for a static example, not real-time.
