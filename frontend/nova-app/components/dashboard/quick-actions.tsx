"use client";

import Link from "next/link";
import { MaterialIcon } from "@/components/ui/material-icon";

export function QuickActions() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Link
        href="/pricing"
        className="glass-card rounded-xl p-5 text-left hover:bg-white/[0.06] transition-colors group"
      >
        <MaterialIcon icon="add_circle" className="text-primary mb-2" />
        <div className="font-headline font-bold text-sm">New Valuation</div>
        <div className="text-[10px] font-mono text-on-surface/30 mt-1">Open pricing agent</div>
      </Link>
      <button className="glass-card rounded-xl p-5 text-left hover:bg-white/[0.06] transition-colors group">
        <MaterialIcon icon="download" className="text-secondary mb-2" />
        <div className="font-headline font-bold text-sm">Export Data</div>
        <div className="text-[10px] font-mono text-on-surface/30 mt-1">Download valuation log</div>
      </button>
      <button className="glass-card rounded-xl p-5 text-left hover:bg-white/[0.06] transition-colors group">
        <MaterialIcon icon="sync" className="text-tertiary mb-2" />
        <div className="font-headline font-bold text-sm">Run Scrapers</div>
        <div className="text-[10px] font-mono text-on-surface/30 mt-1">Refresh market data</div>
      </button>
    </div>
  );
}
