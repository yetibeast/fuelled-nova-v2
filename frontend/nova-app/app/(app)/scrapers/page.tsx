"use client";

import { useEffect, useState, useCallback } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { MaterialIcon } from "@/components/ui/material-icon";
import { ScraperTable, type ScraperTarget } from "@/components/scrapers/scraper-table";
import { AddScraperModal } from "@/components/scrapers/add-scraper-modal";
import { HarvestSection } from "@/components/scrapers/harvest-section";
import { fetchScrapers } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

export default function ScrapersPage() {
  const [scrapers, setScrapers] = useState<ScraperTarget[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);

  const load = useCallback(() => {
    fetchScrapers()
      .then((data: ScraperTarget[]) => { setScrapers(data); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, []);

  useEffect(() => { load(); }, [load]);

  const activeCount = scrapers.filter((s) => s.status === "active").length;
  const totalListings = scrapers.reduce((sum, s) => sum + (s.total_items || 0), 0);
  const withPricing = scrapers.reduce((sum, s) => sum + (s.items_with_price || 0), 0);
  const errorCount = scrapers.filter((s) => s.health_pct < 50).length;
  const lastRefresh = scrapers
    .filter((s) => s.last_run_at)
    .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime())[0]?.last_run_at;

  if (error) {
    return <div className="text-red-400 font-mono text-sm p-4">Error loading scrapers: {error}</div>;
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-6 w-52 bg-white/[0.06] rounded animate-pulse" />
          <div className="h-3 w-72 bg-white/[0.04] rounded animate-pulse mt-2" />
        </div>
        <div className="grid grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="glass-card rounded-xl p-5">
              <div className="h-3 w-16 bg-white/[0.06] rounded animate-pulse mb-2" />
              <div className="h-7 w-12 bg-white/[0.04] rounded animate-pulse" />
            </div>
          ))}
        </div>
        <div className="glass-card rounded-xl p-6">
          <div className="h-4 w-24 bg-white/[0.06] rounded animate-pulse mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 bg-white/[0.04] rounded animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="font-headline font-bold text-xl tracking-tight">Scraper Management</h1>
          <p className="text-on-surface/40 text-xs font-mono mt-1">
            Configure, monitor, and trigger data source scrapers
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-primary/10 border border-primary/20 text-primary text-[11px] font-mono px-4 py-2 rounded-lg hover:bg-primary/20 transition-colors flex items-center gap-2"
        >
          <MaterialIcon icon="add" className="text-[14px]" />
          Add Scraper
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <MetricCard label="Active Scrapers" value={String(activeCount)} subtitle={`of ${scrapers.length}`} />
        <MetricCard label="Total Listings" value={totalListings.toLocaleString()} valueColor="text-secondary" />
        <MetricCard label="With Pricing" value={withPricing.toLocaleString()} valueColor="text-secondary" />
        <MetricCard label="Last Refresh" value={lastRefresh ? timeAgo(lastRefresh) : "---"} />
        <MetricCard
          label="Errors"
          value={String(errorCount)}
          valueColor={errorCount > 0 ? "text-red-400" : "text-emerald-400"}
        />
      </div>

      {/* Scraper Table */}
      <div className="mb-6">
        <ScraperTable scrapers={scrapers} onRefresh={load} />
      </div>

      {/* Sold Price Harvester */}
      <HarvestSection />

      {/* Add Scraper Modal */}
      <AddScraperModal
        open={showAdd}
        onClose={() => setShowAdd(false)}
        onCreated={load}
      />
    </>
  );
}
