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
  seller_name?: string | null;
  seller_account_type?: string | null;
  seller_other_assets_url?: string | null;
  event_contact_name?: string | null;
  event_contact_email?: string | null;
  event_contact_phone?: string | null;
}

interface StaleTargetsTableProps {
  items: StaleTarget[];
  loading: boolean;
  error: boolean;
  isAdmin: boolean;
  promotedIds: Set<string>;
  promotingId: string | null;
  onPromote: (sourceListingId: string) => void;
  onDownloadCsv?: () => void;
  csvDownloading?: boolean;
}

export function StaleTargetsTable({
  items,
  loading,
  error,
  isAdmin,
  promotedIds,
  promotingId,
  onPromote,
  onDownloadCsv,
  csvDownloading,
}: StaleTargetsTableProps) {
  return (
    <div className="glass-card rounded-xl overflow-hidden mb-6">
      <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-start gap-4">
        <div>
          <h3 className="font-headline font-bold text-sm tracking-tight">Stale Acquisition Candidates</h3>
          <p className="text-[10px] font-mono text-on-surface/30 mt-1">
            Ranked competitor listings that look old enough to chase as buy-side opportunities
          </p>
        </div>
        {onDownloadCsv && (
          <button
            onClick={onDownloadCsv}
            disabled={csvDownloading}
            className="px-3 py-1.5 rounded-md border border-primary/20 bg-primary/10 text-[10px] font-mono uppercase tracking-widest text-primary hover:bg-primary/20 transition-all disabled:opacity-50"
          >
            {csvDownloading ? "Exporting..." : "Download CSV"}
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-6 py-3">EQUIPMENT</th>
              <th className="px-6 py-3">SELLER</th>
              <th className="px-6 py-3">CONTACT</th>
              <th className="px-6 py-3 text-right">ASKING</th>
              <th className="px-6 py-3 text-right">DAYS</th>
              <th className="px-6 py-3 text-right">SCORE</th>
              <th className="px-6 py-3">SOURCE</th>
              <th className="px-6 py-3 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
                  Loading stale targets...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
                  Stale target feed not available
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
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
                      <div className="text-[10px] text-on-surface/30 mt-1">
                        {catName(item.category || null)}
                        {item.reason ? ` · ${item.reason}` : ""}
                      </div>
                    </td>
                    <td className="px-6 py-3 text-on-surface/70">
                      <div>
                        {item.seller_name ? (
                          item.seller_other_assets_url ? (
                            <a
                              href={item.seller_other_assets_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-primary/80 hover:text-primary"
                            >
                              {item.seller_name}
                            </a>
                          ) : (
                            item.seller_name
                          )
                        ) : (
                          <span className="text-on-surface/30">—</span>
                        )}
                      </div>
                      {item.seller_account_type && (
                        <div className="text-[10px] text-on-surface/30 mt-1 uppercase tracking-widest">
                          {item.seller_account_type}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-3 text-on-surface/70">
                      {item.event_contact_email ? (
                        <>
                          <div>{item.event_contact_name || "—"}</div>
                          <a
                            href={`mailto:${item.event_contact_email}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-[10px] text-primary/70 hover:text-primary mt-1 block truncate max-w-[180px]"
                          >
                            {item.event_contact_email}
                          </a>
                        </>
                      ) : (
                        <span className="text-on-surface/30">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-right text-secondary font-bold">{formatPrice(item.asking_price)}</td>
                    <td className="px-6 py-3 text-right text-on-surface">
                      <div>{item.days_listed}</div>
                      <div className="text-[10px] text-on-surface/30 mt-1">/ {item.stale_threshold_days}</div>
                    </td>
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
