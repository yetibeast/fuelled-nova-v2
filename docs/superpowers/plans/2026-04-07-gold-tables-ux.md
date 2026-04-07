# Gold Tables UX Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add search, sortable columns, and per-column filters to all 4 Gold Tables tabs so they feel like a lightweight spreadsheet.

**Architecture:** Build a reusable `<FilterableTable>` component that wraps the existing `<DataTable>` with client-side search, sort, and column filters. Each tab component passes its column definitions and data; FilterableTable handles all interactivity. No backend changes — all filtering/sorting is client-side on ~700 rows max.

**Tech Stack:** React (Next.js App Router), TypeScript, Tailwind v4 (inline @theme tokens), existing DataTable + glass-card design system.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `frontend/nova-app/components/ui/filterable-table.tsx` | Reusable table with search bar, sortable headers, column filters |
| Modify | `frontend/nova-app/components/gold/rcn-tab.tsx` | Switch from DataTable to FilterableTable with column defs |
| Modify | `frontend/nova-app/components/gold/market-tab.tsx` | Switch from DataTable to FilterableTable with column defs |
| Modify | `frontend/nova-app/components/gold/depreciation-tab.tsx` | Switch from DataTable to FilterableTable with column defs |
| Modify | `frontend/nova-app/components/gold/gaps-tab.tsx` | Switch from DataTable to FilterableTable with column defs |

---

## Chunk 1: FilterableTable Component

### Task 1: Build FilterableTable

**Files:**
- Create: `frontend/nova-app/components/ui/filterable-table.tsx`

The component accepts a generic column definition and data array. It provides:
- Global search bar (filters across all text columns)
- Clickable column headers for sort (asc/desc/none cycle)
- Per-column filter dropdowns for enum columns, text inputs for free-text columns
- Row count badge that updates with filtering
- Preserves the existing glass-card + DataTable visual style

- [ ] **Step 1: Create FilterableTable component**

```tsx
// frontend/nova-app/components/ui/filterable-table.tsx
"use client";

import { useState, useMemo, ReactNode } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";

export interface ColumnDef<T> {
  key: keyof T & string;
  header: string;
  align?: "left" | "right";
  // "text" = free-text filter input, "select" = dropdown from unique values, "none" = no filter
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

export function FilterableTable<T extends Record<string, unknown>>({
  title, badge, columns, data, rowKey, actions, footer
}: FilterableTableProps<T>) {
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);
  const [colFilters, setColFilters] = useState<Record<string, string>>({});

  // Unique values for select filters
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

  // Filter + sort pipeline
  const filtered = useMemo(() => {
    let rows = data;

    // Global search
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter((row) =>
        columns.some((col) => {
          const v = row[col.key];
          return v != null && String(v).toLowerCase().includes(q);
        })
      );
    }

    // Per-column filters
    for (const [key, val] of Object.entries(colFilters)) {
      if (!val) continue;
      const lower = val.toLowerCase();
      rows = rows.filter((row) => {
        const v = row[key];
        return v != null && String(v).toLowerCase().includes(lower);
      });
    }

    // Sort
    if (sortCol && sortDir) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortCol] ?? "";
        const bv = b[sortCol] ?? "";
        const cmp = typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      });
    }

    return rows;
  }, [data, search, colFilters, sortCol, sortDir, columns]);

  function handleSort(key: string) {
    if (sortCol !== key) { setSortCol(key); setSortDir("asc"); }
    else if (sortDir === "asc") setSortDir("desc");
    else { setSortCol(null); setSortDir(null); }
  }

  function setFilter(key: string, val: string) {
    setColFilters((prev) => ({ ...prev, [key]: val }));
  }

  const hasActions = !!actions;

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header with search */}
      <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <h3 className="font-headline font-bold text-sm tracking-tight">{title}</h3>
          <span className="text-[10px] font-mono text-secondary">
            {filtered.length}{badge ? ` / ${badge}` : ""}
          </span>
        </div>
        <div className="relative">
          <MaterialIcon icon="search" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[14px] text-on-surface/30" />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-surface-container-lowest rounded-lg pl-8 pr-3 py-1.5 text-xs font-mono text-on-surface placeholder:text-on-surface/20 border border-white/[0.06] focus:border-primary/40 focus:outline-none w-56"
          />
        </div>
      </div>

      {/* Column filters row */}
      {columns.some((c) => c.filter && c.filter !== "none") && (
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
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              );
            }
            // text filter
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
                    col.sortable !== false ? "cursor-pointer select-none hover:text-on-surface/50" : ""
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
                <td colSpan={columns.length + (hasActions ? 1 : 0)} className="px-6 py-8 text-center text-on-surface/30">
                  No matching records
                </td>
              </tr>
            ) : (
              filtered.map((row) => (
                <tr key={rowKey(row)} className="hover:bg-white/[0.04] transition-colors">
                  {columns.map((col) => (
                    <td key={col.key} className={`px-6 py-3 ${col.align === "right" ? "text-right" : ""}`}>
                      {col.render(row)}
                    </td>
                  ))}
                  {hasActions && (
                    <td className="px-6 py-3">{actions(row)}</td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      {footer && (
        <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
          {footer}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend/nova-app && npx next build --no-lint 2>&1 | tail -20`
Expected: No TypeScript errors related to filterable-table.tsx

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/ui/filterable-table.tsx
git commit -m "feat: add FilterableTable component with search, sort, column filters"
```

---

### Task 2: Migrate RCN Tab to FilterableTable

**Files:**
- Modify: `frontend/nova-app/components/gold/rcn-tab.tsx`

Preserve existing edit/delete inline functionality via the `actions` prop. Add column filters: manufacturer (text), model (text), class (select), drive (select), status (select).

- [ ] **Step 1: Rewrite RcnTab to use FilterableTable**

Replace the DataTable usage with FilterableTable. Keep the edit/delete state management and handlers. Define columns with appropriate filters and renderers. Pass edit/delete buttons through the `actions` prop.

Key column definitions:
- `canonical_manufacturer`: filter="text", sortable
- `canonical_model`: filter="text", sortable
- `equipment_class`: filter="select", sortable
- `drive_type`: filter="select", sortable
- `escalated_rcn_cad`: filter="none", sortable, align="right", render with formatPrice (or edit input when editing)
- `confidence`: filter="none", sortable, align="right", render as percentage
- `validation_status`: filter="select", sortable, render with color coding

Actions column: edit/save/cancel + delete buttons (same logic as current).

- [ ] **Step 2: Verify it compiles and renders**

Run: `cd frontend/nova-app && npx next build --no-lint 2>&1 | tail -20`

- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/gold/rcn-tab.tsx
git commit -m "feat: RCN tab uses FilterableTable with search/sort/filters"
```

---

### Task 3: Migrate Market Values Tab

**Files:**
- Modify: `frontend/nova-app/components/gold/market-tab.tsx`

Column filters: manufacturer (text), model (text), value_type (select), validation_status (select).

- [ ] **Step 1: Rewrite MarketTab to use FilterableTable**

Define columns matching current headers. No actions column (read-only tab).

- [ ] **Step 2: Verify build**
- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/gold/market-tab.tsx
git commit -m "feat: Market tab uses FilterableTable with search/sort/filters"
```

---

### Task 4: Migrate Depreciation Tab

**Files:**
- Modify: `frontend/nova-app/components/gold/depreciation-tab.tsx`

Column filters: equipment_class (select), manufacturer (text), model (text).

- [ ] **Step 1: Rewrite DepreciationTab to use FilterableTable**
- [ ] **Step 2: Verify build**
- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/gold/depreciation-tab.tsx
git commit -m "feat: Depreciation tab uses FilterableTable with search/sort/filters"
```

---

### Task 5: Migrate Coverage Gaps Tab

**Files:**
- Modify: `frontend/nova-app/components/gold/gaps-tab.tsx`

Column filters: none needed (only ~20 rows). Just add sort on all columns. Keep the color-coded status rendering.

- [ ] **Step 1: Rewrite GapsTab to use FilterableTable**
- [ ] **Step 2: Verify build**
- [ ] **Step 3: Commit**

```bash
git add frontend/nova-app/components/gold/gaps-tab.tsx
git commit -m "feat: Coverage gaps tab uses FilterableTable with sorting"
```

---

### Task 6: Final verification

- [ ] **Step 1: Full build check**

Run: `cd frontend/nova-app && npx next build --no-lint 2>&1 | tail -30`
Expected: Clean build, zero errors.

- [ ] **Step 2: Commit all if any stragglers**

---

## Future Enhancements (Phase 2+)

These are intentionally deferred:
- **Inline editing on Market + Depreciation tabs** (needs backend PUT endpoints)
- **CSV export** button per tab
- **Bulk select + bulk actions** (validate/reject multiple rows)
- **Add new record** modal per tab (RCN already has backend POST)
- **Server-side pagination** (only needed if data exceeds ~1000 rows)
- **Column resize / reorder** (full spreadsheet feel)
- **Sticky headers** for long scroll
