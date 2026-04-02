"use client";

import { useEffect, useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchHarvestStats, triggerHarvest } from "@/lib/api";

interface HarvestStats {
  total_closed_auctions: number;
  harvested: number;
  remaining: number;
  sources: Record<string, number>;
}

export function HarvestSection() {
  const [stats, setStats] = useState<HarvestStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [harvesting, setHarvesting] = useState(false);

  useEffect(() => {
    fetchHarvestStats()
      .then((data: HarvestStats) => { setStats(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  async function handleHarvest() {
    setHarvesting(true);
    try {
      await triggerHarvest();
      const fresh = await fetchHarvestStats();
      setStats(fresh);
    } catch { /* silently fail */ }
    setHarvesting(false);
  }

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-6">
        <div className="h-4 w-40 bg-white/[0.06] rounded animate-pulse mb-4" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-white/[0.04] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const sources = Object.entries(stats.sources || {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="glass-card rounded-xl p-6">
      <div className="flex justify-between items-center mb-5">
        <div>
          <h3 className="font-headline font-bold text-sm tracking-tight">Sold Price Harvester</h3>
          <p className="text-[10px] font-mono text-on-surface/30 mt-1">
            Captures final transaction prices from closed auctions
          </p>
        </div>
        <button
          onClick={handleHarvest}
          disabled={harvesting}
          className="bg-primary/10 border border-primary/20 text-primary text-[11px] font-mono px-4 py-2 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-40 flex items-center gap-2"
        >
          <MaterialIcon icon="bolt" className="text-[14px]" />
          {harvesting ? "Harvesting..." : "Harvest Now"}
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="bg-white/[0.03] rounded-lg p-3">
          <div className="text-[10px] font-mono text-on-surface/30 uppercase tracking-widest mb-1">
            Closed Auctions
          </div>
          <div className="text-lg font-headline font-bold text-on-surface">
            {stats.total_closed_auctions.toLocaleString()}
          </div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3">
          <div className="text-[10px] font-mono text-on-surface/30 uppercase tracking-widest mb-1">
            Harvested
          </div>
          <div className="text-lg font-headline font-bold text-secondary">
            {stats.harvested.toLocaleString()}
          </div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-3">
          <div className="text-[10px] font-mono text-on-surface/30 uppercase tracking-widest mb-1">
            Remaining
          </div>
          <div className="text-lg font-headline font-bold text-primary">
            {stats.remaining.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Source breakdown */}
      {sources.length > 0 && (
        <div>
          <div className="text-[10px] font-mono text-on-surface/30 uppercase tracking-widest mb-2">
            Source Breakdown
          </div>
          <div className="flex flex-wrap gap-3">
            {sources.map(([name, count]) => (
              <div
                key={name}
                className="bg-white/[0.04] rounded px-3 py-1.5 flex items-center gap-2"
              >
                <span className="text-[11px] font-mono text-on-surface/60">{name}</span>
                <span className="text-[11px] font-mono text-secondary font-bold">
                  {count.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
