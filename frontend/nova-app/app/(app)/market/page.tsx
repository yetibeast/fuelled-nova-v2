"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { CategoriesTable } from "@/components/market/categories-table";
import { DataHealth } from "@/components/market/data-health";
import { CoverageGaps } from "@/components/market/coverage-gaps";
import { MarketSourcesTable } from "@/components/market/sources-table";
import { fetchHealth } from "@/lib/api";

export default function MarketPage() {
  const [listingCount, setListingCount] = useState("--");

  useEffect(() => {
    fetchHealth()
      .then((data: { listings_count?: number }) => {
        setListingCount((data.listings_count || 0).toLocaleString());
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Market Intelligence</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          Live data from 16 sources across Western Canada and US
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Active Listings" value={listingCount} />
        <MetricCard label="Sources Connected" value="16" valueColor="text-secondary" />
        <MetricCard label="Last Refresh" value="Today" />
        <MetricCard label="Coverage" value="Western CA + US" valueColor="text-white" />
      </div>

      {/* Categories */}
      <div className="mb-6">
        <CategoriesTable />
      </div>

      {/* Data Health */}
      <div className="mb-6">
        <DataHealth />
      </div>

      {/* Coverage Gaps */}
      <div className="mb-6">
        <CoverageGaps />
      </div>

      {/* Sources */}
      <MarketSourcesTable />
    </>
  );
}
