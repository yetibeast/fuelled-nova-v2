"use client";

import { useEffect, useState } from "react";
import { FilterableTable, ColumnDef } from "@/components/ui/filterable-table";
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

const columns: ColumnDef<DepRow>[] = [
  {
    key: "equipment_class",
    header: "CLASS",
    filter: "select",
    render: (r) => <span className="text-on-surface font-medium">{r.equipment_class || "---"}</span>,
  },
  {
    key: "canonical_manufacturer",
    header: "MANUFACTURER",
    filter: "text",
    render: (r) => <span className="text-on-surface/70">{r.canonical_manufacturer || "---"}</span>,
  },
  {
    key: "canonical_model",
    header: "MODEL",
    filter: "text",
    render: (r) => <span className="text-on-surface/50">{r.canonical_model || "---"}</span>,
  },
  {
    key: "age_years",
    header: "AGE (YRS)",
    align: "right",
    filter: "none",
    render: (r) => <span className="text-on-surface/70">{r.age_years ?? "---"}</span>,
  },
  {
    key: "retention_ratio",
    header: "RETENTION",
    align: "right",
    filter: "none",
    render: (r) => (
      <span className="text-secondary font-bold">
        {r.retention_ratio != null ? (r.retention_ratio * 100).toFixed(1) + "%" : "---"}
      </span>
    ),
  },
  {
    key: "effective_date",
    header: "DATE",
    filter: "none",
    render: (r) => <span className="text-on-surface/40">{r.effective_date || "---"}</span>,
  },
];

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
    <FilterableTable<DepRow>
      title="Depreciation Observations"
      badge={`${rows.length} OBS`}
      columns={columns}
      data={rows}
      rowKey={(r) => r.id}
    />
  );
}
