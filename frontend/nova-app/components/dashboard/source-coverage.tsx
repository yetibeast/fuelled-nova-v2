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

export function SourceCoverage() {
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [totalListings, setTotalListings] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchMarketSources()
      .then((data: SourceRow[]) => {
        setSources(data);
        setTotalListings(data.reduce((sum: number, s: SourceRow) => sum + (s.total || 0), 0));
      })
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <DataTable title="Market Data Coverage" headers={["SOURCE", "LISTINGS", "WITH PRICE", "LAST UPDATED", "STATUS"]} headerAligns={["left", "right", "right", "left", "left"]}>
        <tr><td colSpan={5} className="px-6 py-6 text-center text-on-surface/30 text-xs font-mono">Unable to load source data</td></tr>
      </DataTable>
    );
  }

  return (
    <DataTable
      title="Market Data Coverage"
      subtitle="Scraped competitor listings across Western Canada and US"
      headers={["SOURCE", "LISTINGS", "WITH PRICE", "LAST UPDATED", "STATUS"]}
      headerAligns={["left", "right", "right", "left", "left"]}
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
        </tr>
      ))}
    </DataTable>
  );
}
