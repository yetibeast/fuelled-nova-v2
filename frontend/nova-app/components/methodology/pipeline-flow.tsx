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
