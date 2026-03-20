"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { fetchHealth, fetchRecentValuations } from "@/lib/api";

export function MetricCards() {
  const [listings, setListings] = useState<string>("--");
  const [valuationsToday, setValuationsToday] = useState<string>("\u2014");

  useEffect(() => {
    fetchHealth()
      .then((d) => setListings((d.listings_count || 0).toLocaleString()))
      .catch(() => {});

    fetchRecentValuations()
      .then((rows: { timestamp?: string }[]) => {
        const today = new Date().toISOString().slice(0, 10);
        const count = rows.filter(
          (v) => (v.timestamp || "").slice(0, 10) === today
        ).length;
        if (count > 0) setValuationsToday(String(count));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard label="Total Listings" value={listings} subtitle="Live database" />
      <MetricCard label="Valuations Today" value={valuationsToday} subtitle="Pricing queries" />
      <MetricCard label="Avg Confidence" value="HIGH" valueColor="text-secondary" subtitle="Last 7 days" subtitleColor="text-on-surface/30" />
      <MetricCard label="Data Sources" value="16" subtitle="All active" subtitleColor="text-emerald-400" />
    </div>
  );
}
