"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchGoldGaps } from "@/lib/api";
import { catName } from "@/lib/utils";

interface GapRow {
  category: string;
  listing_count: number;
  rcn_refs: number;
  market_refs: number;
}

export function GapsTab() {
  const [rows, setRows] = useState<GapRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldGaps()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  return (
    <DataTable
      title="Coverage Gaps"
      badge={`${rows.length} GAPS`}
      headers={["CATEGORY", "LISTINGS", "RCN REFS", "MARKET REFS", "STATUS"]}
      headerAligns={["left", "right", "right", "right", "left"]}
    >
      {rows.map((r) => {
        const hasRcn = r.rcn_refs > 0;
        const hasMkt = r.market_refs >= 3;
        return (
          <tr key={r.category} className="hover:bg-white/[0.04] transition-colors">
            <td className="px-6 py-3 text-on-surface font-medium">{catName(r.category)}</td>
            <td className="px-6 py-3 text-right text-on-surface/70">{r.listing_count.toLocaleString()}</td>
            <td className="px-6 py-3 text-right">
              <span className={hasRcn ? "text-emerald-400" : "text-red-400 font-bold"}>
                {r.rcn_refs}
              </span>
            </td>
            <td className="px-6 py-3 text-right">
              <span className={hasMkt ? "text-emerald-400" : "text-amber-400 font-bold"}>
                {r.market_refs}
              </span>
            </td>
            <td className="px-6 py-3">
              <span className={`text-xs font-mono ${
                hasRcn && hasMkt ? "text-emerald-400" :
                !hasRcn && !hasMkt ? "text-red-400" : "text-amber-400"
              }`}>
                {hasRcn && hasMkt ? "Covered" : !hasRcn ? "No RCN" : "Low Market Data"}
              </span>
            </td>
          </tr>
        );
      })}
    </DataTable>
  );
}
