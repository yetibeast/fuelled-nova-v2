"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchGoldDepreciation } from "@/lib/api";

interface DepRow {
  id: string;
  equipment_class: string | null;
  canonical_manufacturer: string | null;
  canonical_model: string | null;
  age_years: number | null;
  retention_ratio: number | null;
  effective_date: string | null;
}

export function DepreciationTab() {
  const [rows, setRows] = useState<DepRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldDepreciation()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  return (
    <DataTable
      title="Depreciation Observations"
      badge={`${rows.length} OBS`}
      headers={["CLASS", "MANUFACTURER", "MODEL", "AGE (YRS)", "RETENTION", "DATE"]}
      headerAligns={["left", "left", "left", "right", "right", "left"]}
    >
      {rows.map((r) => (
        <tr key={r.id} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface font-medium">{r.equipment_class || "---"}</td>
          <td className="px-6 py-3 text-on-surface/70">{r.canonical_manufacturer || "---"}</td>
          <td className="px-6 py-3 text-on-surface/50">{r.canonical_model || "---"}</td>
          <td className="px-6 py-3 text-right text-on-surface/70">{r.age_years ?? "---"}</td>
          <td className="px-6 py-3 text-right text-secondary font-bold">
            {r.retention_ratio != null ? (r.retention_ratio * 100).toFixed(1) + "%" : "---"}
          </td>
          <td className="px-6 py-3 text-on-surface/40">{r.effective_date || "---"}</td>
        </tr>
      ))}
    </DataTable>
  );
}
