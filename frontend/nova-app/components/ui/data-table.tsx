"use client";

import { ReactNode } from "react";

interface DataTableProps {
  title: string;
  subtitle?: string;
  badge?: string;
  headers: string[];
  headerAligns?: ("left" | "right")[];
  children: ReactNode;
  footer?: ReactNode;
}

export function DataTable({ title, subtitle, badge, headers, headerAligns, children, footer }: DataTableProps) {
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center">
        <div>
          <h3 className="font-headline font-bold text-sm tracking-tight">{title}</h3>
          {subtitle && (
            <p className="text-[10px] font-mono text-on-surface/30 mt-1">{subtitle}</p>
          )}
        </div>
        {badge && <span className="text-[10px] font-mono text-secondary">{badge}</span>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              {headers.map((h, i) => (
                <th
                  key={i}
                  className={`px-6 py-3 font-medium ${headerAligns?.[i] === "right" ? "text-right" : ""}`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">{children}</tbody>
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
