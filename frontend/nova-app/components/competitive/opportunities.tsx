"use client";

import { catName, formatPrice } from "@/lib/utils";

interface Opportunity {
  title?: string;
  category?: string;
  asking_price?: number;
  median_price?: number;
  discount_pct?: number;
  source?: string;
  url?: string;
}

interface OpportunitiesTableProps {
  opps: Opportunity[];
  error: boolean;
}

export function OpportunitiesTable({ opps, error }: OpportunitiesTableProps) {
  return (
    <div className="overflow-x-auto border-t border-white/[0.06]">
      <table className="w-full text-left font-mono text-xs">
        <thead className="text-on-surface/30 border-b border-white/[0.05]">
          <tr>
            <th className="px-6 py-3">EQUIPMENT</th>
            <th className="px-6 py-3">CATEGORY</th>
            <th className="px-6 py-3 text-right">LISTED PRICE</th>
            <th className="px-6 py-3 text-right">PEER MEDIAN</th>
            <th className="px-6 py-3 text-right">DISCOUNT</th>
            <th className="px-6 py-3">SOURCE</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {error || opps.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-6 py-6 text-center text-on-surface/30">
                {error ? "Analysis endpoint not available" : "No below-market listings found"}
              </td>
            </tr>
          ) : (
            opps.map((o, i) => (
              <tr
                key={i}
                className={`hover:bg-white/[0.04] transition-colors ${o.url ? "cursor-pointer" : ""}`}
                onClick={o.url ? () => window.open(o.url, "_blank") : undefined}
              >
                <td className="px-6 py-3 text-on-surface">{(o.title || "---").slice(0, 55)}</td>
                <td className="px-6 py-3 text-on-surface/50">{catName(o.category || null)}</td>
                <td className="px-6 py-3 text-right text-secondary font-bold">
                  {formatPrice(o.asking_price)}
                </td>
                <td className="px-6 py-3 text-right text-on-surface/50">
                  {formatPrice(o.median_price)}
                </td>
                <td className="px-6 py-3 text-right">
                  <span className="text-primary font-bold">{o.discount_pct || 0}% below</span>
                </td>
                <td className="px-6 py-3 text-on-surface/40">{o.source || "---"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      {!error && opps.length > 0 && (
        <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
          {opps.length} listings below 50% of peer median (similar-priced items in same category)
        </div>
      )}
    </div>
  );
}
