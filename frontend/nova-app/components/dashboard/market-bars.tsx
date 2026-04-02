"use client";

import { useEffect, useState } from "react";
import { fetchMarketCategories } from "@/lib/api";
import { catName } from "@/lib/utils";

interface CategoryRow {
  category: string | null;
  total: number;
}

/* Categories relevant to Fuelled's oilfield equipment business */
const CORE_CATEGORIES = new Set([
  "compressor_package",
  "compressor",
  "pump_jack",
  "pumpjack",
  "tank",
  "separator",
  "treater",
  "pump",
  "generator",
  "flare_knockout",
  "flare_ko",
  "amine",
  "dehydrator",
  "vessel",
  "meter",
  "vru",
]);

export function MarketBars() {
  const [cats, setCats] = useState<CategoryRow[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchMarketCategories()
      .then((data: CategoryRow[]) => {
        const relevant = data.filter(
          (c) => c.category != null && CORE_CATEGORIES.has(c.category.toLowerCase())
        );
        setCats(relevant.length > 0 ? relevant.slice(0, 8) : data.filter((c) => c.category != null).slice(0, 8));
      })
      .catch(() => setError(true));
  }, []);

  const max = Math.max(...cats.map((c) => c.total), 1);

  if (error) {
    return (
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Market Overview</h3>
        <p className="text-on-surface/30 text-xs font-mono">Unable to load market data</p>
      </div>
    );
  }

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
