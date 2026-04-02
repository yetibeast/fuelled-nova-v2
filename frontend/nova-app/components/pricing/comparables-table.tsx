"use client";

import { formatPrice } from "@/lib/utils";

interface Comparable {
  title?: string;
  year?: string | number;
  location?: string;
  price?: number;
  currency?: string;
  url?: string;
}

interface ComparablesTableProps {
  comparables: Comparable[];
  currency?: string;
}

export function ComparablesTable({ comparables, currency }: ComparablesTableProps) {
  if (!comparables.length) return null;

  return (
    <div className="glass-card overflow-hidden rounded-xl">
      <div className="px-6 py-4 bg-white/5 border-b border-white/5 flex justify-between items-center">
        <h3 className="font-headline font-bold text-sm tracking-tight text-on-surface">
          Recent Market Comparables
        </h3>
        <span className="text-[10px] font-mono text-secondary">
          {comparables.length} MATCHES FOUND
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/40 border-b border-white/5">
            <tr>
              <th className="px-6 py-3 font-medium">UNIT SPEC</th>
              <th className="px-6 py-3 font-medium">YEAR</th>
              <th className="px-6 py-3 font-medium">REGION</th>
              <th className="px-6 py-3 font-medium text-right">
                LIST PRICE
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {comparables.map((c, i) => (
              <tr
                key={i}
                className={`hover:bg-white/10 transition-colors group ${c.url ? "cursor-pointer" : ""}`}
                onClick={
                  c.url
                    ? () => window.open(c.url, "_blank", "noopener")
                    : undefined
                }
              >
                <td className="px-6 py-4 text-on-surface font-medium">
                  {c.title || "-"}
                </td>
                <td className="px-6 py-4 text-on-surface/70">
                  {c.year || "-"}
                </td>
                <td className="px-6 py-4 text-on-surface/70">
                  {c.location || "-"}
                </td>
                <td className="px-6 py-4 text-right text-secondary font-bold">
                  {formatPrice(c.price ?? 0)}{" "}
                  <span className="text-on-surface/40 font-normal">{c.currency || currency || "CAD"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
