"use client";

import { useState, useMemo, ReactNode } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";

export interface ColumnDef<T> {
  key: keyof T & string;
  header: string;
  align?: "left" | "right";
  filter?: "text" | "select" | "none";
  sortable?: boolean;
  render: (row: T) => ReactNode;
}

interface FilterableTableProps<T> {
  title: string;
  badge?: string;
  columns: ColumnDef<T>[];
  data: T[];
  rowKey: (row: T) => string;
  actions?: (row: T) => ReactNode;
  footer?: ReactNode;
}

type SortDir = "asc" | "desc" | null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function FilterableTable<T extends Record<string, any>>({
  title, badge, columns, data, rowKey, actions, footer,
}: FilterableTableProps<T>) {
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [colFilters, setColFilters] = useState<Record<string, string>>({});

  const selectOptions = useMemo(() => {
    const opts: Record<string, string[]> = {};
    for (const col of columns) {
      if (col.filter === "select") {
        const vals = new Set<string>();
        for (const row of data) {
          const v = row[col.key];
          if (v != null && v !== "") vals.add(String(v));
        }
        opts[col.key] = Array.from(vals).sort();
      }
    }
    return opts;
  }, [data, columns]);

  const filtered = useMemo(() => {
    let rows = data;

    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter((row) =>
        columns.some((col) => {
          const v = row[col.key];
          return v != null && String(v).toLowerCase().includes(q);
        })
      );
    }

    for (const [key, val] of Object.entries(colFilters)) {
      if (!val) continue;
      const lower = val.toLowerCase();
      rows = rows.filter((row) => {
        const v = row[key];
        return v != null && String(v).toLowerCase().includes(lower);
      });
    }

    if (sortCol && sortDir) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortCol] ?? "";
        const bv = b[sortCol] ?? "";
        const cmp =
          typeof av === "number" && typeof bv === "number"
            ? av - bv
            : String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      });
    }

    return rows;
  }, [data, search, colFilters, sortCol, sortDir, columns]);

  function handleSort(key: string) {
    if (sortCol !== key) {
      setSortCol(key);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortCol(null);
      setSortDir(null);
    }
  }

  function setFilter(key: string, val: string) {
    setColFilters((prev) => ({ ...prev, [key]: val }));
  }

  const hasFilters = columns.some((c) => c.filter && c.filter !== "none");
  const hasActions = !!actions;

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <h3 className="font-headline font-bold text-sm tracking-tight">{title}</h3>
          <span className="text-[10px] font-mono text-secondary">
            {filtered.length}{badge ? ` / ${badge}` : ""}
          </span>
        </div>
        <div className="relative">
          <MaterialIcon
            icon="search"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[14px] text-on-surface/30"
          />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface-container-lowest rounded-lg pl-8 pr-3 py-1.5 text-xs font-mono text-on-surface placeholder:text-on-surface/20 border border-white/[0.06] focus:border-primary/40 focus:outline-none w-56"
          />
        </div>
      </div>

      {/* Column filters */}
      {hasFilters && (
        <div className="px-6 py-2 border-b border-white/[0.04] flex gap-2 items-center flex-wrap">
          <span className="text-[10px] font-mono text-on-surface/20 mr-1">FILTERS</span>
          {columns.map((col) => {
            if (!col.filter || col.filter === "none") return null;
            if (col.filter === "select") {
              return (
                <select
                  key={col.key}
                  value={colFilters[col.key] || ""}
                  onChange={(e) => setFilter(col.key, e.target.value)}
                  className="bg-surface-container-lowest rounded px-2 py-1 text-[10px] font-mono text-on-surface/70 border border-white/[0.06] focus:border-primary/40 focus:outline-none"
                >
                  <option value="">{col.header}: All</option>
                  {(selectOptions[col.key] || []).map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              );
            }
            return (
              <input
                key={col.key}
                type="text"
                placeholder={col.header}
                value={colFilters[col.key] || ""}
                onChange={(e) => setFilter(col.key, e.target.value)}
                className="bg-surface-container-lowest rounded px-2 py-1 text-[10px] font-mono text-on-surface/70 placeholder:text-on-surface/20 border border-white/[0.06] focus:border-primary/40 focus:outline-none w-28"
              />
            );
          })}
          {Object.values(colFilters).some(Boolean) && (
            <button
              onClick={() => setColFilters({})}
              className="text-[10px] font-mono text-primary/60 hover:text-primary ml-1"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-6 py-3 font-medium ${col.align === "right" ? "text-right" : ""} ${
                    col.sortable !== false
                      ? "cursor-pointer select-none hover:text-on-surface/50"
                      : ""
                  }`}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable !== false && sortCol === col.key && (
                      <MaterialIcon
                        icon={sortDir === "asc" ? "arrow_upward" : "arrow_downward"}
                        className="text-[12px] text-primary"
                      />
                    )}
                  </span>
                </th>
              ))}
              {hasActions && <th className="px-6 py-3 font-medium" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length + (hasActions ? 1 : 0)}
                  className="px-6 py-8 text-center text-on-surface/30"
                >
                  No matching records
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <tr key={rowKey(row)} className="hover:bg-white/[0.04] transition-colors">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-6 py-3 ${col.align === "right" ? "text-right" : ""}`}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                  {hasActions && <td className="px-6 py-3">{actions(row)}</td>}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {footer && (
        <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
          {footer}
        </div>
      )}
    </div>
  );
}
