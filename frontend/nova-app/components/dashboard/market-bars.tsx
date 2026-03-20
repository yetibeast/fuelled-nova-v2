"use client";

import { useEffect, useState } from "react";
import { fetchMarketCategories } from "@/lib/api";
import { catName } from "@/lib/utils";

interface CategoryRow {
  category: string | null;
  total: number;
}

export function MarketBars() {
  const [cats, setCats] = useState<CategoryRow[]>([]);

  useEffect(() => {
    fetchMarketCategories()
      .then((data: CategoryRow[]) => {
        const filtered = data.filter((c) => c.category != null);
        setCats(filtered.slice(0, 8));
      })
      .catch(() => {
        setCats([
          { category: "Compressor Package", total: 2141 },
          { category: "Separator", total: 1800 },
          { category: "Pump", total: 1500 },
          { category: "Tank", total: 2300 },
          { category: "Generator", total: 800 },
        ]);
      });
  }, []);

  const max = Math.max(...cats.map((c) => c.total), 1);

  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      <h3 className="font-headline font-bold text-sm tracking-tight mb-4">
        Market Overview
      </h3>
      <div className="space-y-3">
        {cats.map((c, i) => {
          const pct = Math.round((c.total / max) * 100);
          return (
            <div key={i} className="flex items-center gap-4">
              <div className="w-36 text-xs text-on-surface/60 truncate">
                {catName(c.category)}
              </div>
              <div className="flex-1 stat-bar">
                <div
                  className="stat-bar-fill bg-secondary/60"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="w-16 text-right text-xs font-mono text-secondary">
                {(c.total || 0).toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
