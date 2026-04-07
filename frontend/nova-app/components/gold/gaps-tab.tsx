"use client";

import { useEffect, useState, useMemo } from "react";
import { FilterableTable, ColumnDef } from "@/components/ui/filterable-table";
import { fetchGoldGaps } from "@/lib/api";
import { catName } from "@/lib/utils";

interface GapRowRaw {
  category: string;
  listing_count: number;
  rcn_refs: number;
  market_refs: number;
}

interface GapRow extends GapRowRaw {
  status: string;
}

const columns: ColumnDef<GapRow>[] = [
  {
    key: "category",
    header: "CATEGORY",
    filter: "none",
    render: (r) => <span className="text-on-surface font-medium">{catName(r.category)}</span>,
  },
  {
    key: "listing_count",
    header: "LISTINGS",
    align: "right",
    filter: "none",
    render: (r) => <span className="text-on-surface/70">{r.listing_count.toLocaleString()}</span>,
  },
  {
    key: "rcn_refs",
    header: "RCN REFS",
    align: "right",
    filter: "none",
    render: (r) => (
      <span className={r.rcn_refs > 0 ? "text-emerald-400" : "text-red-400 font-bold"}>
        {r.rcn_refs}
      </span>
    ),
  },
  {
    key: "market_refs",
    header: "MARKET REFS",
    align: "right",
    filter: "none",
    render: (r) => (
      <span className={r.market_refs >= 3 ? "text-emerald-400" : "text-amber-400 font-bold"}>
        {r.market_refs}
      </span>
    ),
  },
  {
    key: "status",
    header: "STATUS",
    filter: "select",
    render: (r) => (
      <span
        className={`text-xs font-mono ${
          r.status === "Covered"
            ? "text-emerald-400"
            : r.status === "No RCN"
              ? "text-red-400"
              : "text-amber-400"
        }`}
      >
        {r.status}
      </span>
    ),
  },
];

export function GapsTab() {
  const [rawRows, setRawRows] = useState<GapRowRaw[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGoldGaps()
      .then(setRawRows)
      .catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo<GapRow[]>(
    () =>
      rawRows.map((r) => ({
        ...r,
        status:
          r.rcn_refs > 0 && r.market_refs >= 3
            ? "Covered"
            : r.rcn_refs === 0
              ? "No RCN"
              : "Low Market Data",
      })),
    [rawRows]
  );

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  return (
    <FilterableTable<GapRow>
      title="Coverage Gaps"
      badge={`${rows.length} GAPS`}
      columns={columns}
      data={rows}
      rowKey={(r) => r.category}
    />
  );
}
