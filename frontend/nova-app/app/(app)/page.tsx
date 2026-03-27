"use client";

import { Suspense } from "react";
import { MetricCards } from "@/components/dashboard/metric-cards";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { MarketBars } from "@/components/dashboard/market-bars";
import { SourceCoverage } from "@/components/dashboard/source-coverage";
import { Opportunities } from "@/components/dashboard/opportunities";
import { QuickActions } from "@/components/dashboard/quick-actions";

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div><div className="h-6 w-40 bg-white/[0.06] rounded animate-pulse" /><div className="h-3 w-64 bg-white/[0.04] rounded animate-pulse mt-2" /></div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[1,2,3,4].map(i => <div key={i} className="glass-card rounded-xl p-5"><div className="h-3 w-16 bg-white/[0.06] rounded animate-pulse mb-2" /><div className="h-7 w-12 bg-white/[0.04] rounded animate-pulse" /></div>)}</div>
      <div className="glass-card rounded-xl p-6"><div className="h-4 w-36 bg-white/[0.06] rounded animate-pulse mb-4" /><div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-10 bg-white/[0.04] rounded animate-pulse" />)}</div></div>
      <div className="glass-card rounded-xl p-6 h-48 animate-pulse bg-white/[0.03]" />
    </div>
  );
}

export default function DashboardPage() {
  const dateStr = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <Suspense fallback={<DashboardSkeleton />}>
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
    </Suspense>
  );
}
