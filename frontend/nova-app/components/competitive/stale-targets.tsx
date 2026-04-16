"use client";

import { catName, formatPrice } from "@/lib/utils";

export interface StaleTarget {
  source_listing_id: string;
  title?: string;
  category?: string;
  asking_price?: number;
  days_listed: number;
  stale_threshold_days: number;
  peer_median?: number | null;
  acquisition_score: number;
  source?: string;
  url?: string;
  promotable: boolean;
  reason?: string;
}

interface StaleTargetsTableProps {
  items: StaleTarget[];
  loading: boolean;
  error: boolean;
  isAdmin: boolean;
  promotedIds: Set<string>;
  promotingId: string | null;
  onPromote: (sourceListingId: string) => void;
}

export function StaleTargetsTable({
  items,
  loading,
  error,
  isAdmin,
  promotedIds,
  promotingId,
  onPromote,
}: StaleTargetsTableProps) {
  return (
    <div className="glass-card rounded-xl overflow-hidden mb-6">
      <div className="px-6 py-4 border-b border-white/[0.06]">
        <h3 className="font-headline font-bold text-sm tracking-tight">Stale Acquisition Candidates</h3>
        <p className="text-[10px] font-mono text-on-surface/30 mt-1">
          Ranked competitor listings that look old enough to chase as buy-side opportunities
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-6 py-3">EQUIPMENT</th>
              <th className="px-6 py-3">CATEGORY</th>
              <th className="px-6 py-3 text-right">ASKING</th>
              <th className="px-6 py-3 text-right">DAYS</th>
              <th className="px-6 py-3 text-right">THRESHOLD</th>
              <th className="px-6 py-3 text-right">PEER MEDIAN</th>
              <th className="px-6 py-3 text-right">SCORE</th>
              <th className="px-6 py-3">SOURCE</th>
              <th className="px-6 py-3 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              <tr>
                <td colSpan={9} className="px-6 py-6 text-center text-on-surface/30">
                  Loading stale targets...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={9} className="px-6 py-6 text-center text-on-surface/30">
                  Stale target feed not available
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-6 py-6 text-center text-on-surface/30">
                  No stale acquisition candidates found
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const alreadyPromoted = promotedIds.has(item.source_listing_id);
                const canPromote = isAdmin && item.promotable && !alreadyPromoted;
                return (
                  <tr
                    key={item.source_listing_id}
                    className={`hover:bg-white/[0.04] transition-colors ${item.url ? "cursor-pointer" : ""}`}
                    onClick={item.url ? () => window.open(item.url, "_blank") : undefined}
                  >
                    <td className="px-6 py-3 text-on-surface">
                      <div>{(item.title || "---").slice(0, 52)}</div>
                      {item.reason && (
                        <div className="text-[10px] text-on-surface/30 mt-1">{item.reason}</div>
                      )}
                    </td>
                    <td className="px-6 py-3 text-on-surface/50">{catName(item.category || null)}</td>
                    <td className="px-6 py-3 text-right text-secondary font-bold">{formatPrice(item.asking_price)}</td>
                    <td className="px-6 py-3 text-right text-on-surface">{item.days_listed}</td>
                    <td className="px-6 py-3 text-right text-on-surface/40">{item.stale_threshold_days}</td>
                    <td className="px-6 py-3 text-right text-on-surface/50">{formatPrice(item.peer_median)}</td>
                    <td className="px-6 py-3 text-right">
                      <span className="text-primary font-bold">{item.acquisition_score}</span>
                    </td>
                    <td className="px-6 py-3 text-on-surface/40">{item.source || "---"}</td>
                    <td className="px-6 py-3 text-right">
                      {alreadyPromoted ? (
                        <span className="text-[10px] text-emerald-400 uppercase tracking-widest">Promoted</span>
                      ) : canPromote ? (
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            onPromote(item.source_listing_id);
                          }}
                          disabled={promotingId === item.source_listing_id}
                          className="px-3 py-1 rounded-md border border-primary/20 bg-primary/10 text-primary hover:bg-primary/20 transition-all"
                        >
                          {promotingId === item.source_listing_id ? "Promoting..." : "Promote"}
                        </button>
                      ) : (
                        <span className="text-[10px] text-on-surface/30 uppercase tracking-widest">
                          {item.promotable ? "View" : "Auction"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
