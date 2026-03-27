"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchGoldMarket } from "@/lib/api";
import { formatPrice } from "@/lib/utils";

interface MarketRow {
  id: string;
  canonical_manufacturer: string;
  canonical_model: string;
  value_type: string | null;
  normalized_value_cad: number | null;
  validation_status: string | null;
  effective_date: string | null;
}

export function MarketTab() {
  const [rows, setRows] = useState<MarketRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldMarket()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  return (
    <DataTable
      title="Market Value References"
      badge={`${rows.length} REFS`}
      headers={["MANUFACTURER", "MODEL", "TYPE", "VALUE (CAD)", "STATUS", "DATE"]}
      headerAligns={["left", "left", "left", "right", "left", "left"]}
    >
      {rows.map((r) => (
        <tr key={r.id} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface font-medium">{r.canonical_manufacturer}</td>
          <td className="px-6 py-3 text-on-surface/70">{r.canonical_model}</td>
          <td className="px-6 py-3 text-on-surface/50">{r.value_type || "---"}</td>
          <td className="px-6 py-3 text-right text-secondary font-bold">
            {formatPrice(r.normalized_value_cad)}
          </td>
          <td className="px-6 py-3 text-on-surface/50">{r.validation_status || "---"}</td>
          <td className="px-6 py-3 text-on-surface/40">{r.effective_date || "---"}</td>
        </tr>
      ))}
    </DataTable>
  );
}
