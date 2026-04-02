"use client";

import { useEffect, useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchGoldGaps } from "@/lib/api";

export function CoverageGaps() {
  const [gaps, setGaps] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldGaps()
      .then((data: string[]) => {
        setGaps(data);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (error) {
    return (
      <div className="glass-card rounded-xl p-6 text-red-400 font-mono text-xs">
        Failed to load coverage gaps: {error}
      </div>
    );
  }

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
        {loading ? (
          <p className="text-xs text-on-surface/40 font-mono">Loading gaps...</p>
        ) : gaps.length === 0 ? (
          <p className="text-xs text-emerald-400 font-mono">No coverage gaps detected</p>
        ) : (
          <ul className="space-y-2">
            {gaps.map((g, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-on-surface/50">
                <span className="text-amber-400 mt-0.5">&#8226;</span>
                <span>{typeof g === "string" ? g : JSON.stringify(g)}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="text-[10px] font-mono text-on-surface/25 mt-4">
          These categories rely on Claude&apos;s general knowledge instead of gold-table data.
          Adding 3-5 RCN references per category would significantly improve accuracy.
        </p>
      </div>
    </div>
  );
}
