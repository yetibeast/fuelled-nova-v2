"use client";

import { MetricCards } from "@/components/dashboard/metric-cards";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { MarketBars } from "@/components/dashboard/market-bars";
import { SourceCoverage } from "@/components/dashboard/source-coverage";
import { Opportunities } from "@/components/dashboard/opportunities";
import { QuickActions } from "@/components/dashboard/quick-actions";

export default function DashboardPage() {
  const dateStr = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-headline font-bold text-xl tracking-tight">Dashboard</h1>
          <p className="text-on-surface/40 text-xs font-mono mt-1">
            Equipment valuation intelligence
          </p>
        </div>
        <span className="text-[10px] font-mono text-secondary">{dateStr}</span>
      </div>

      {/* Metric Cards */}
      <MetricCards />

      {/* Recent Valuations */}
      <div className="mb-6">
        <RecentActivity />
      </div>

      {/* Market Overview */}
      <MarketBars />

      {/* Market Data Coverage */}
      <div className="mb-6">
        <SourceCoverage />
      </div>

      {/* Market Opportunities (lazy) */}
      <Opportunities />

      {/* Quick Actions */}
      <QuickActions />
    </>
  );
}
