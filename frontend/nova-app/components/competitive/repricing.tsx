"use client";

import { catName, formatPrice } from "@/lib/utils";

interface RepricingItem {
  title?: string;
  category?: string;
  asking_price?: number;
  median_price?: number;
  discount_pct?: number;
  neighbor_count?: number;
  url?: string;
}

interface RepricingTableProps {
  items: RepricingItem[];
  error: boolean;
}

export function RepricingTable({ items, error }: RepricingTableProps) {
  return (
    <div className="border-t border-white/[0.06]">
      <div
        className="px-6 py-4 border-b border-white/[0.06]"
        style={{ background: "rgba(239,93,40,0.03)" }}
      >
        <div className="flex justify-between items-center">
          <h3 className="font-headline font-bold text-sm tracking-tight">
            Fuelled Listings &mdash; Potential Repricing Needed
          </h3>
          <span className="text-[10px] font-mono text-primary">REVIEW</span>
        </div>
        <p className="text-[10px] font-mono text-on-surface/30 mt-1">
          Our listings that may be priced below market &mdash; review recommended
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-6 py-3">EQUIPMENT</th>
              <th className="px-6 py-3">CATEGORY</th>
              <th className="px-6 py-3 text-right">OUR PRICE</th>
              <th className="px-6 py-3 text-right">PEER MEDIAN</th>
              <th className="px-6 py-3 text-right">BELOW BY</th>
              <th className="px-6 py-3 text-right">PEERS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {error || items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-6 text-center text-on-surface/30">
                  {error ? "Repricing endpoint not available" : "No Fuelled listings flagged for repricing"}
                </td>
              </tr>
            ) : (
              items.map((o, i) => (
                <tr
                  key={i}
                  className={`hover:bg-white/[0.04] transition-colors ${o.url ? "cursor-pointer" : ""}`}
                  onClick={o.url ? () => window.open(o.url, "_blank") : undefined}
                >
                  <td className="px-6 py-3 text-on-surface">{(o.title || "---").slice(0, 55)}</td>
                  <td className="px-6 py-3 text-on-surface/50">{catName(o.category || null)}</td>
                  <td className="px-6 py-3 text-right text-primary font-bold">
                    {formatPrice(o.asking_price)}
                  </td>
                  <td className="px-6 py-3 text-right text-on-surface/50">
                    {formatPrice(o.median_price)}
                  </td>
                  <td className="px-6 py-3 text-right">
                    <span className="text-primary font-bold">{o.discount_pct || 0}%</span>
                  </td>
                  <td className="px-6 py-3 text-right text-on-surface/40">
                    {o.neighbor_count || 0}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!error && items.length > 0 && (
        <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
          {items.length} Fuelled listings below 60% of peer median
        </div>
      )}
    </div>
  );
}
