"use client";

import { useState } from "react";
import { fetchMarketOpportunities, fetchMarketRepricing } from "@/lib/api";
import { MaterialIcon } from "@/components/ui/material-icon";
import { catName, formatPrice } from "@/lib/utils";

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

export function Opportunities() {
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [repricing, setRepricing] = useState<Opportunity[]>([]);

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
    <div className="glass-card rounded-xl overflow-hidden mb-6">
      <div className="px-6 py-4 flex justify-between items-center">
        <div>
          <h3 className="font-headline font-bold text-sm tracking-tight">
            Market Opportunities
          </h3>
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
        <div>
          {/* Opportunities table */}
          <div className="overflow-x-auto border-t border-white/[0.06]">
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-on-surface/30 border-b border-white/[0.05]">
                <tr>
                  <th className="px-6 py-3">EQUIPMENT</th>
                  <th className="px-6 py-3">CATEGORY</th>
                  <th className="px-6 py-3 text-right">LISTED PRICE</th>
                  <th className="px-6 py-3 text-right">PEER MEDIAN</th>
                  <th className="px-6 py-3 text-right">DISCOUNT</th>
                  <th className="px-6 py-3">SOURCE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {error || opps.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-on-surface/30">
                      {error ? "Analysis endpoint not available" : "No below-market listings found"}
                    </td>
                  </tr>
                ) : (
                  opps.map((o, i) => (
                    <tr
                      key={i}
                      className={`hover:bg-white/[0.04] transition-colors ${o.url ? "cursor-pointer" : ""}`}
                      onClick={o.url ? () => window.open(o.url, "_blank") : undefined}
                    >
                      <td className="px-6 py-3 text-on-surface">
                        {(o.title || "---").slice(0, 55)}
                      </td>
                      <td className="px-6 py-3 text-on-surface/50">{catName(o.category || null)}</td>
                      <td className="px-6 py-3 text-right text-secondary font-bold">
                        {formatPrice(o.asking_price)}
                      </td>
                      <td className="px-6 py-3 text-right text-on-surface/50">
                        {formatPrice(o.median_price)}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <span className="text-primary font-bold">
                          {o.discount_pct || 0}% below
                        </span>
                      </td>
                      <td className="px-6 py-3 text-on-surface/40">{o.source || "---"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {!error && opps.length > 0 && (
            <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
              {opps.length} listings below 50% of peer median (similar-priced items in same category)
            </div>
          )}

          {/* Fuelled Repricing */}
          <div className="border-t border-white/[0.06]">
            <div
              className="px-6 py-4 border-b border-white/[0.06]"
              style={{ background: "rgba(239,93,40,0.03)" }}
            >
              <div className="flex justify-between items-center">
                <h3 className="font-headline font-bold text-sm tracking-tight">
                  Fuelled Listings &mdash; Potential Repricing Needed
                </h3>
                <span className="text-[10px] font-mono text-primary">REVIEW</span>
              </div>
              <p className="text-[10px] font-mono text-on-surface/30 mt-1">
                Our listings that may be priced below market &mdash; review recommended
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs">
                <thead className="text-on-surface/30 border-b border-white/[0.05]">
                  <tr>
                    <th className="px-6 py-3">EQUIPMENT</th>
                    <th className="px-6 py-3">CATEGORY</th>
                    <th className="px-6 py-3 text-right">OUR PRICE</th>
                    <th className="px-6 py-3 text-right">PEER MEDIAN</th>
                    <th className="px-6 py-3 text-right">BELOW BY</th>
                    <th className="px-6 py-3 text-right">PEERS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {error || repricing.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-6 text-center text-on-surface/30">
                        {error
                          ? "Repricing endpoint not available"
                          : "No Fuelled listings flagged for repricing"}
                      </td>
                    </tr>
                  ) : (
                    repricing.map((o, i) => (
                      <tr
                        key={i}
                        className={`hover:bg-white/[0.04] transition-colors ${o.url ? "cursor-pointer" : ""}`}
                        onClick={o.url ? () => window.open(o.url, "_blank") : undefined}
                      >
                        <td className="px-6 py-3 text-on-surface">
                          {(o.title || "---").slice(0, 55)}
                        </td>
                        <td className="px-6 py-3 text-on-surface/50">
                          {catName(o.category || null)}
                        </td>
                        <td className="px-6 py-3 text-right text-primary font-bold">
                          {formatPrice(o.asking_price)}
                        </td>
                        <td className="px-6 py-3 text-right text-on-surface/50">
                          {formatPrice(o.median_price)}
                        </td>
                        <td className="px-6 py-3 text-right">
                          <span className="text-primary font-bold">{o.discount_pct || 0}%</span>
                        </td>
                        <td className="px-6 py-3 text-right text-on-surface/40">
                          {o.neighbor_count || 0}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            {!error && repricing.length > 0 && (
              <div className="px-6 py-3 border-t border-white/[0.06] text-[10px] font-mono text-on-surface/20">
                {repricing.length} Fuelled listings below 60% of peer median
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
