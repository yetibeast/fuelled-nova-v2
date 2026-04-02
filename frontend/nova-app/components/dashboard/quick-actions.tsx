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
      <Link
        href="/competitive"
        className="glass-card rounded-xl p-5 text-left hover:bg-white/[0.06] transition-colors group"
      >
        <MaterialIcon icon="insights" className="text-secondary mb-2" />
        <div className="font-headline font-bold text-sm">Market Intelligence</div>
        <div className="text-[10px] font-mono text-on-surface/30 mt-1">Competitive analysis</div>
      </Link>
      <Link
        href="/market-data"
        className="glass-card rounded-xl p-5 text-left hover:bg-white/[0.06] transition-colors group"
      >
        <MaterialIcon icon="database" className="text-tertiary mb-2" />
        <div className="font-headline font-bold text-sm">Market Data</div>
        <div className="text-[10px] font-mono text-on-surface/30 mt-1">Browse categories &amp; sources</div>
      </Link>
    </div>
  );
}
