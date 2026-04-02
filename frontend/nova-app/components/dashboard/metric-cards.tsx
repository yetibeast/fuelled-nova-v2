"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { fetchHealth, fetchRecentValuations, fetchMarketSources } from "@/lib/api";

export function MetricCards() {
  const [listings, setListings] = useState<string>("--");
  const [valuationsToday, setValuationsToday] = useState<string>("\u2014");
  const [confidence, setConfidence] = useState<string>("--");
  const [sourceCount, setSourceCount] = useState<string>("--");

  useEffect(() => {
    fetchHealth()
      .then((d) => setListings((d.listings_count || 0).toLocaleString()))
      .catch(() => {});

    fetchRecentValuations()
      .then((rows: { timestamp?: string; confidence?: string }[]) => {
        const today = new Date().toISOString().slice(0, 10);
        const count = rows.filter(
          (v) => (v.timestamp || "").slice(0, 10) === today
        ).length;
        if (count > 0) setValuationsToday(String(count));

        // Compute average confidence from recent valuations
        if (rows.length > 0) {
          const confMap: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
          const scored = rows
            .map((v) => confMap[(v.confidence || "").toUpperCase()] || 0)
            .filter((s) => s > 0);
          if (scored.length > 0) {
            const avg = scored.reduce((a, b) => a + b, 0) / scored.length;
            setConfidence(avg >= 2.5 ? "HIGH" : avg >= 1.5 ? "MED" : "LOW");
          }
        }
      })
      .catch(() => {});

    fetchMarketSources()
      .then((data: { source: string }[]) => {
        setSourceCount(String(data.length));
      })
      .catch(() => {});
  }, []);

  const confColor = confidence === "HIGH" ? "text-secondary" : confidence === "MED" ? "text-amber-400" : "text-on-surface/50";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <MetricCard label="Total Listings" value={listings} subtitle="Live database" />
      <MetricCard label="Valuations Today" value={valuationsToday} subtitle="Pricing queries" />
      <MetricCard label="Avg Confidence" value={confidence} valueColor={confColor} subtitle="Recent valuations" subtitleColor="text-on-surface/30" />
      <MetricCard label="Data Sources" value={sourceCount} subtitle="All active" subtitleColor="text-emerald-400" />
    </div>
  );
}
