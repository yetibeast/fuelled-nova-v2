"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { MaterialIcon } from "@/components/ui/material-icon";
import { CompetitiveSourceCoverage } from "@/components/competitive/source-coverage";
import { OpportunitiesTable } from "@/components/competitive/opportunities";
import { RepricingTable } from "@/components/competitive/repricing";
import { fetchMarketSources, fetchMarketOpportunities, fetchMarketRepricing } from "@/lib/api";

interface Opportunity {
  title?: string;
  category?: string;
  asking_price?: number;
  median_price?: number;
  discount_pct?: number;
  source?: string;
  url?: string;
  neighbor_count?: number;
}

export default function CompetitivePage() {
  const [competitorCount, setCompetitorCount] = useState("--");
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [repricing, setRepricing] = useState<Opportunity[]>([]);

  useEffect(() => {
    fetchMarketSources()
      .then((data: { source: string; total: number }[]) => {
        const nonFuelled = data
          .filter((s) => (s.source || "").toLowerCase() !== "fuelled")
          .reduce((sum, s) => sum + (s.total || 0), 0);
        setCompetitorCount(nonFuelled.toLocaleString());
      })
      .catch(() => {});
  }, []);

  function handleLoad() {
    setLoading(true);
    setError(false);
    Promise.all([fetchMarketOpportunities(), fetchMarketRepricing()])
      .then(([oppsData, repricingData]) => {
        setOpps(oppsData);
        setRepricing(repricingData);
        setLoaded(true);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
        setLoaded(true);
      });
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Competitive Intelligence</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          Monitor competitor listings and identify market opportunities
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricCard label="Competitor Data" value={competitorCount} subtitle="Non-Fuelled listings" />
        <MetricCard label="New This Week" value="847" subtitle="Across all sources" />
        <MetricCard label="Stale Inventory" value="3,210" subtitle="Listed > 1 year w/ no sale" />
      </div>

      {/* Source coverage */}
      <div className="mb-6">
        <CompetitiveSourceCoverage />
      </div>

      {/* Opportunities (lazy-loaded) */}
      <div className="glass-card rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 flex justify-between items-center">
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight">Below-Market Deals</h3>
            <p className="text-[10px] font-mono text-on-surface/30 mt-1">
              Non-Fuelled listings priced below median of similar-priced peers
            </p>
          </div>
          {!loaded && (
            <button
              onClick={handleLoad}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-primary/10 border border-primary/20 text-xs font-mono text-primary hover:bg-primary/20 transition-all flex items-center gap-2"
            >
              {loading ? (
                <>
                  <MaterialIcon icon="progress_activity" className="text-[16px] animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <MaterialIcon icon="query_stats" className="text-[16px]" />
                  Load Analysis
                </>
              )}
            </button>
          )}
        </div>

        {loaded && (
          <>
            <OpportunitiesTable opps={opps} error={error} />
            <RepricingTable items={repricing} error={error} />
          </>
        )}
      </div>
    </>
  );
}
