"use client";

import { useEffect, useState } from "react";
import { FilterableTable, ColumnDef } from "@/components/ui/filterable-table";
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

const columns: ColumnDef<MarketRow>[] = [
  {
    key: "canonical_manufacturer",
    header: "MANUFACTURER",
    filter: "text",
    render: (r) => <span className="text-on-surface font-medium">{r.canonical_manufacturer}</span>,
  },
  {
    key: "canonical_model",
    header: "MODEL",
    filter: "text",
    render: (r) => <span className="text-on-surface/70">{r.canonical_model}</span>,
  },
  {
    key: "value_type",
    header: "TYPE",
    filter: "select",
    render: (r) => <span className="text-on-surface/50">{r.value_type || "---"}</span>,
  },
  {
    key: "normalized_value_cad",
    header: "VALUE (CAD)",
    align: "right",
    filter: "none",
    render: (r) => <span className="text-secondary font-bold">{formatPrice(r.normalized_value_cad)}</span>,
  },
  {
    key: "validation_status",
    header: "STATUS",
    filter: "select",
    render: (r) => <span className="text-on-surface/50">{r.validation_status || "---"}</span>,
  },
  {
    key: "effective_date",
    header: "DATE",
    filter: "none",
    render: (r) => <span className="text-on-surface/40">{r.effective_date || "---"}</span>,
  },
];

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
    <FilterableTable<MarketRow>
      title="Market Value References"
      badge={`${rows.length} REFS`}
      columns={columns}
      data={rows}
      rowKey={(r) => r.id}
    />
  );
}
