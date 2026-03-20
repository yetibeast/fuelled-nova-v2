"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

const GAPS = [
  "OTSG / Steam Generation -- 0 RCN anchors, fallback only",
  "Water Treatment -- 0 RCN anchors",
  "Electrical Distribution -- 0 RCN anchors",
];

export function CoverageGaps() {
  return (
    <div className="glass-card rounded-xl overflow-hidden border-amber-500/20">
      <div className="px-6 py-4 border-b border-white/[0.06] flex items-center gap-2">
        <MaterialIcon icon="warning" className="text-[18px] text-amber-400" />
        <h3 className="font-headline font-bold text-sm tracking-tight">Coverage Gaps</h3>
      </div>
      <div className="px-6 py-4">
        <p className="text-[11px] font-mono text-amber-400/80 mb-3 uppercase tracking-wider">
          Equipment categories with no RCN reference data
        </p>
        <ul className="space-y-2">
          {GAPS.map((g, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-on-surface/50">
              <span className="text-amber-400 mt-0.5">&#8226;</span>
              <span>{g}</span>
            </li>
          ))}
        </ul>
        <p className="text-[10px] font-mono text-on-surface/25 mt-4">
          These categories rely on Claude&apos;s general knowledge instead of gold-table data.
          Adding 3-5 RCN references per category would significantly improve accuracy.
        </p>
      </div>
    </div>
  );
}
