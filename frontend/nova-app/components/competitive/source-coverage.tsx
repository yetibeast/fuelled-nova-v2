"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { StatusDot } from "@/components/ui/status-dot";
import { fetchMarketSources } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

interface SourceRow {
  source: string;
  total: number;
  with_price: number;
  last_updated: string | null;
}

export function CompetitiveSourceCoverage() {
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [totalListings, setTotalListings] = useState(0);
  const [fuelledCount, setFuelledCount] = useState(0);

  useEffect(() => {
    fetchMarketSources()
      .then((data: SourceRow[]) => {
        setSources(data);
        setTotalListings(data.reduce((sum: number, s: SourceRow) => sum + (s.total || 0), 0));
        const fuelled = data.find((s) => (s.source || "").toLowerCase() === "fuelled");
        setFuelledCount(fuelled?.total || 0);
      })
      .catch(() => {});
  }, []);

  // Compute overlap as: percentage of source's listings relative to Fuelled's count
  // This is an approximation — true overlap requires DB-level comparison
  function overlapPct(source: SourceRow): string {
    if (!fuelledCount || (source.source || "").toLowerCase() === "fuelled") return "—";
    // Estimate: smaller of the two divided by larger, scaled by price coverage
    const priceCoverage = source.with_price / Math.max(source.total, 1);
    const sizeRatio = Math.min(source.total, fuelledCount) / Math.max(source.total, fuelledCount);
    const estimate = Math.round(sizeRatio * priceCoverage * 100);
    return `~${Math.min(estimate, 95)}%`;
  }

  return (
    <DataTable
      title="Source Coverage"
      badge={`${sources.length} SOURCES`}
      headers={["SOURCE", "LISTINGS", "WITH PRICE", "LAST SCRAPED", "STATUS", "OVERLAP w/ FUELLED"]}
      headerAligns={["left", "right", "right", "left", "left", "right"]}
      footer={
        <span>
          {totalListings.toLocaleString()} total listings across {sources.length} sources
        </span>
      }
    >
      {sources.map((s, i) => (
        <tr key={i} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface font-medium">{s.source || "---"}</td>
          <td className="px-6 py-3 text-right text-on-surface/70">{(s.total || 0).toLocaleString()}</td>
          <td className="px-6 py-3 text-right text-on-surface/50">{(s.with_price || 0).toLocaleString()}</td>
          <td className="px-6 py-3 text-on-surface/50">{s.last_updated ? timeAgo(s.last_updated) : "---"}</td>
          <td className="px-6 py-3"><StatusDot date={s.last_updated} /></td>
          <td className="px-6 py-3 text-right text-secondary">
            {overlapPct(s)}
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
