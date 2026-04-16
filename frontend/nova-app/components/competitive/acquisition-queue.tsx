"use client";

import { catName, formatPrice } from "@/lib/utils";

const STATUSES = ["new", "watching", "contacted", "negotiating", "drafted", "won", "lost", "archived"];

export interface AcquisitionSummary {
  total: number;
  new: number;
  watching: number;
  contacted: number;
  negotiating: number;
  drafted: number;
  won: number;
  lost: number;
  archived: number;
}

export interface AcquisitionTarget {
  id: string;
  source_listing_id: string;
  title?: string;
  category?: string;
  asking_price?: number;
  peer_median?: number | null;
  acquisition_score: number;
  source?: string;
  url?: string;
  status: string;
  assigned_to?: string | null;
  updated_at?: string;
  draft_payload?: Record<string, unknown> | null;
}

interface AcquisitionQueueProps {
  summary: AcquisitionSummary | null;
  items: AcquisitionTarget[];
  loading: boolean;
  error: boolean;
  updatingId: string | null;
  draftingId: string | null;
  onStatusChange: (targetId: string, status: string) => void;
  onGenerateDraft: (targetId: string) => void;
}

export function AcquisitionQueue({
  summary,
  items,
  loading,
  error,
  updatingId,
  draftingId,
  onStatusChange,
  onGenerateDraft,
}: AcquisitionQueueProps) {
  return (
    <div className="glass-card rounded-xl overflow-hidden mb-6">
      <div className="px-6 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight">Acquisition Queue</h3>
            <p className="text-[10px] font-mono text-on-surface/30 mt-1">
              Admin workflow for promoted stale targets and draft Fuelled listing packets
            </p>
          </div>
          <div className="flex gap-2 flex-wrap justify-end">
            <span className="rounded-md border border-white/[0.08] px-2 py-1 text-[10px] font-mono text-on-surface/40">
              Total {summary?.total ?? 0}
            </span>
            <span className="rounded-md border border-white/[0.08] px-2 py-1 text-[10px] font-mono text-on-surface/40">
              New {summary?.new ?? 0}
            </span>
            <span className="rounded-md border border-white/[0.08] px-2 py-1 text-[10px] font-mono text-on-surface/40">
              Contacted {summary?.contacted ?? 0}
            </span>
            <span className="rounded-md border border-white/[0.08] px-2 py-1 text-[10px] font-mono text-on-surface/40">
              Drafted {summary?.drafted ?? 0}
            </span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/30 border-b border-white/[0.05]">
            <tr>
              <th className="px-6 py-3">EQUIPMENT</th>
              <th className="px-6 py-3">CATEGORY</th>
              <th className="px-6 py-3 text-right">ASKING</th>
              <th className="px-6 py-3 text-right">PEER MEDIAN</th>
              <th className="px-6 py-3 text-right">SCORE</th>
              <th className="px-6 py-3">STATUS</th>
              <th className="px-6 py-3">DRAFT</th>
              <th className="px-6 py-3 text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
                  Loading acquisition queue...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
                  Acquisition queue not available
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-6 text-center text-on-surface/30">
                  No acquisition targets promoted yet
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.id}
                  className={`hover:bg-white/[0.04] transition-colors ${item.url ? "cursor-pointer" : ""}`}
                  onClick={item.url ? () => window.open(item.url, "_blank") : undefined}
                >
                  <td className="px-6 py-3 text-on-surface">{(item.title || "---").slice(0, 52)}</td>
                  <td className="px-6 py-3 text-on-surface/50">{catName(item.category || null)}</td>
                  <td className="px-6 py-3 text-right text-secondary font-bold">{formatPrice(item.asking_price)}</td>
                  <td className="px-6 py-3 text-right text-on-surface/50">{formatPrice(item.peer_median)}</td>
                  <td className="px-6 py-3 text-right">
                    <span className="text-primary font-bold">{item.acquisition_score}</span>
                  </td>
                  <td className="px-6 py-3">
                    <select
                      value={item.status}
                      onClick={(event) => event.stopPropagation()}
                      onChange={(event) => onStatusChange(item.id, event.target.value)}
                      disabled={updatingId === item.id}
                      className="rounded-md border border-white/[0.08] bg-transparent px-2 py-1 text-[11px] text-on-surface"
                    >
                      {STATUSES.map((status) => (
                        <option key={status} value={status} className="bg-surface text-on-surface">
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-6 py-3 text-on-surface/40">
                    {item.draft_payload ? "Ready" : "Pending"}
                  </td>
                  <td className="px-6 py-3 text-right">
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        onGenerateDraft(item.id);
                      }}
                      disabled={draftingId === item.id}
                      className="px-3 py-1 rounded-md border border-primary/20 bg-primary/10 text-primary hover:bg-primary/20 transition-all"
                    >
                      {draftingId === item.id ? "Drafting..." : "Draft"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
