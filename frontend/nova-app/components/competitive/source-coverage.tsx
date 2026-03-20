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

const OVERLAP_PLACEHOLDERS: Record<string, string> = {
  bidspotter: "12%",
  reflowx: "8%",
  kijiji: "22%",
  equipmenttrader: "15%",
  ironplanet: "11%",
  ironhub: "6%",
  govplanet: "4%",
  surplusrecord: "3%",
  machinio: "9%",
  boomandbucket: "7%",
};

export function CompetitiveSourceCoverage() {
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [totalListings, setTotalListings] = useState(0);

  useEffect(() => {
    fetchMarketSources()
      .then((data: SourceRow[]) => {
        setSources(data);
        setTotalListings(data.reduce((sum: number, s: SourceRow) => sum + (s.total || 0), 0));
      })
      .catch(() => {});
  }, []);

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
            {OVERLAP_PLACEHOLDERS[(s.source || "").toLowerCase()] || "5%"}
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
