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

export function MarketSourcesTable() {
  const [sources, setSources] = useState<SourceRow[]>([]);

  useEffect(() => {
    fetchMarketSources()
      .then((data: SourceRow[]) => setSources(data))
      .catch(() => {});
  }, []);

  return (
    <DataTable
      title="Data Sources"
      badge={`${sources.length} SOURCES`}
      headers={["SOURCE", "LISTINGS", "WITH PRICE", "LAST SCRAPED", "STATUS"]}
      headerAligns={["left", "right", "right", "left", "left"]}
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
