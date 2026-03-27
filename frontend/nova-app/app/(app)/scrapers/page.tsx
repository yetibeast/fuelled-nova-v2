"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/ui/data-table";
import { fetchScrapers } from "@/lib/api";
import { timeAgo, statusDotClass } from "@/lib/utils";

interface Source {
  name: string;
  total_listings: number;
  with_price: number;
  last_run_at: string | null;
  last_run_status: string | null;
  items_found: number | null;
  items_new: number | null;
  last_error: string | null;
}

function statusLabel(s: Source): string {
  if (s.last_error) return "Error";
  if (!s.last_run_at) return "Never";
  const hrs = (Date.now() - new Date(s.last_run_at).getTime()) / 3600000;
  if (hrs < 48) return "OK";
  return "Stale";
}

export default function ScrapersPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScrapers()
      .then((data: Source[]) => { setSources(data); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, []);

  const totalListings = sources.reduce((sum, s) => sum + s.total_listings, 0);
  const lastRefresh = sources
    .filter((s) => s.last_run_at)
    .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime())[0]?.last_run_at;

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error loading scrapers: {error}</div>;

  if (loading) {
    return (
      <div className="space-y-6">
        <div><div className="h-6 w-52 bg-white/[0.06] rounded animate-pulse" /><div className="h-3 w-72 bg-white/[0.04] rounded animate-pulse mt-2" /></div>
        <div className="grid grid-cols-3 gap-4">{[1,2,3].map(i => <div key={i} className="glass-card rounded-xl p-5"><div className="h-3 w-16 bg-white/[0.06] rounded animate-pulse mb-2" /><div className="h-7 w-12 bg-white/[0.04] rounded animate-pulse" /></div>)}</div>
        <div className="glass-card rounded-xl p-6"><div className="h-4 w-24 bg-white/[0.06] rounded animate-pulse mb-4" /><div className="space-y-3">{[1,2,3,4].map(i => <div key={i} className="h-10 bg-white/[0.04] rounded animate-pulse" />)}</div></div>
      </div>
    );
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Scraper Management</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">Data source status and listing counts</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <MetricCard label="Total Sources" value={String(sources.length)} />
        <MetricCard label="Total Listings" value={totalListings.toLocaleString()} valueColor="text-secondary" />
        <MetricCard label="Last Full Refresh" value={lastRefresh ? timeAgo(lastRefresh) : "---"} />
      </div>

      <DataTable
        title="Sources"
        badge={`${sources.length} SOURCES`}
        headers={["SOURCE", "LISTINGS", "WITH PRICE", "LAST RUN", "STATUS", ""]}
        headerAligns={["left", "right", "right", "left", "left", "left"]}
        footer={
          <button
            onClick={() => console.log("manual trigger not yet wired")}
            className="text-primary hover:text-primary/80 transition-colors"
          >
            Refresh All
          </button>
        }
      >
        {sources.map((s) => {
          const dotCls = s.last_error ? "status-red" : statusDotClass(s.last_run_at);
          const isExpanded = expanded === s.name;
          return (
            <tr key={s.name} className="group">
              <td className="px-6 py-3 text-on-surface font-medium">{s.name || "---"}</td>
              <td className="px-6 py-3 text-right text-on-surface/70">{s.total_listings.toLocaleString()}</td>
              <td className="px-6 py-3 text-right text-on-surface/50">{s.with_price.toLocaleString()}</td>
              <td className="px-6 py-3 text-on-surface/50">{s.last_run_at ? timeAgo(s.last_run_at) : "---"}</td>
              <td className="px-6 py-3">
                <span className="flex items-center gap-2">
                  <span className={`status-dot ${dotCls}`} />
                  <span className="text-on-surface/50">{statusLabel(s)}</span>
                </span>
              </td>
              <td className="px-6 py-3">
                {s.last_error && (
                  <button
                    onClick={() => setExpanded(isExpanded ? null : s.name)}
                    className="text-[10px] font-mono text-primary hover:text-primary/80"
                  >
                    {isExpanded ? "Hide" : "Error"}
                  </button>
                )}
                {isExpanded && s.last_error && (
                  <div className="mt-2 p-2 rounded bg-red-500/10 border border-red-500/20 text-[11px] font-mono text-red-400 max-w-xs break-words">
                    {s.last_error}
                  </div>
                )}
              </td>
            </tr>
          );
        })}
      </DataTable>
    </>
  );
}
