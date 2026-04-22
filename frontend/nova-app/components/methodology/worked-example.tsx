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
