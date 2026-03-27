"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { MaterialIcon } from "@/components/ui/material-icon";
import { CompetitiveSourceCoverage } from "@/components/competitive/source-coverage";
import { OpportunitiesTable } from "@/components/competitive/opportunities";
import { RepricingTable } from "@/components/competitive/repricing";
import {
  fetchCompetitiveSummary,
  fetchMarketOpportunities,
  fetchMarketRepricing,
} from "@/lib/api";

interface Summary {
  competitor_total: number;
  new_this_week: number;
  stale_count: number;
}

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
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [repricing, setRepricing] = useState<Opportunity[]>([]);

  useEffect(() => {
    fetchCompetitiveSummary()
      .then((data: Summary) => setSummary(data))
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricCard
          label="Competitor Data"
          value={summary ? summary.competitor_total.toLocaleString() : "--"}
          subtitle="Non-Fuelled listings"
        />
        <MetricCard
          label="New This Week"
          value={summary ? summary.new_this_week.toLocaleString() : "--"}
          subtitle="Across all sources"
        />
        <MetricCard
          label="Stale Inventory"
          value={summary ? summary.stale_count.toLocaleString() : "--"}
          subtitle="Listed > 1 year w/ no sale"
        />
      </div>

      <div className="mb-6">
        <CompetitiveSourceCoverage />
      </div>

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
                  <MaterialIcon icon="autorenew" className="text-[16px] animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <MaterialIcon icon="insights" className="text-[16px]" />
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
