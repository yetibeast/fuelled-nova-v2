"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchMarketCategories } from "@/lib/api";
import { catName, formatPrice } from "@/lib/utils";

interface CategoryRow {
  category: string;
  total: number;
  with_price: number;
  avg_price: number | null;
  min_price: number | null;
  max_price: number | null;
}

export function CategoriesTable() {
  const [categories, setCategories] = useState<CategoryRow[]>([]);

  useEffect(() => {
    fetchMarketCategories()
      .then((data: CategoryRow[]) => setCategories(data))
      .catch(() => {});
  }, []);

  return (
    <DataTable
      title="Listings by Category"
      badge="LIVE DATA"
      headers={["CATEGORY", "TOTAL", "WITH PRICE", "AVG PRICE", "MIN", "MAX"]}
      headerAligns={["left", "right", "right", "right", "right", "right"]}
    >
      {categories.map((c, i) => (
        <tr key={i} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface font-medium">{catName(c.category)}</td>
          <td className="px-6 py-3 text-right text-on-surface/70">{(c.total || 0).toLocaleString()}</td>
          <td className="px-6 py-3 text-right text-on-surface/50">{(c.with_price || 0).toLocaleString()}</td>
          <td className="px-6 py-3 text-right text-secondary font-bold">{formatPrice(c.avg_price)}</td>
          <td className="px-6 py-3 text-right text-on-surface/40">{formatPrice(c.min_price)}</td>
          <td className="px-6 py-3 text-right text-on-surface/40">{formatPrice(c.max_price)}</td>
        </tr>
      ))}
    </DataTable>
  );
}
