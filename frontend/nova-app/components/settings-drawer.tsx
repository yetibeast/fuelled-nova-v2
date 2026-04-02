"use client";

import { useState, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchRecentValuations, fetchFeedback, getStoredUser } from "@/lib/api";
import { timeAgo, formatPrice } from "@/lib/utils";

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsDrawer({ open, onClose }: SettingsDrawerProps) {
  const [queries, setQueries] = useState("--");
  const [monthly, setMonthly] = useState("--");
  const [feedback, setFeedback] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    if (!open) return;
    fetchRecentValuations()
      .then((rows: Array<Record<string, string>>) => {
        const now = new Date().toISOString().slice(0, 10);
        const month = new Date().toISOString().slice(0, 7);
        const today = rows.filter((r) => (r.timestamp || "").slice(0, 10) === now).length;
        const monthlyCount = rows.filter((r) => (r.timestamp || "").slice(0, 7) === month).length;
        setQueries(String(today));
        setMonthly(String(monthlyCount));
      })
      .catch(() => {});
    fetchFeedback("down")
      .then(setFeedback)
      .catch(() => {});
  }, [open]);

  function handleClearHistory() {
    if (confirm("Clear all conversation history from localStorage?")) {
      const user = getStoredUser();
      const key = user?.id ? `nova_conversations_${user.id}` : "nova_conversations";
      localStorage.removeItem(key);
      alert("Conversation history cleared.");
    }
  }

  async function handleExportLog() {
    try {
      const data = await fetchRecentValuations();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "nova_valuation_log.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
  }

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/50 z-[60]" onClick={onClose} />
      )}
      <div
        className={`fixed top-0 right-0 h-full w-[400px] max-w-[90vw] frosted-panel z-[70] flex flex-col transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ borderRight: "none", borderLeft: "1px solid rgba(255,255,255,0.08)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/[0.06]">
          <h2 className="font-headline font-bold text-base tracking-tight">Settings</h2>
          <button onClick={onClose} className="text-on-surface/40 hover:text-on-surface transition-colors">
            <MaterialIcon icon="close" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* API Usage */}
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight mb-4">API Usage</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1">Today</div>
                <div className="text-lg font-mono font-bold text-white">{queries} <span className="text-xs font-normal text-on-surface/40">queries</span></div>
              </div>
              <div>
                <div className="text-[10px] font-mono text-on-surface/40 uppercase tracking-widest mb-1">This Month</div>
                <div className="text-lg font-mono font-bold text-white">{monthly}</div>
              </div>
            </div>
          </div>

          {/* Configuration */}
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Configuration</h3>
            <div className="space-y-3 font-mono text-xs">
              {[
                ["PRICING_V2_ENABLED", <span key="a" className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 text-[10px] font-bold">Active</span>],
                ["Database", <span key="b" className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 text-[10px] font-bold">Connected</span>],
                ["Model", <span key="c" className="text-on-surface/80">Claude Sonnet (latest)</span>],
                ["Reference Data", <span key="d" className="text-secondary">RCN anchors loaded</span>],
              ].map(([label, val], i) => (
                <div key={i} className="flex justify-between items-center py-2 border-b border-white/[0.04] last:border-0">
                  <span className="text-on-surface/60">{label}</span>
                  {val}
                </div>
              ))}
            </div>
          </div>

          {/* Recent Negative Feedback */}
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Recent Feedback</h3>
            {feedback.length === 0 ? (
              <p className="text-[10px] font-mono text-on-surface/30">No negative feedback yet</p>
            ) : (
              <div className="space-y-2">
                {feedback.slice(0, 5).map((fb, i) => (
                  <div key={i} className="glass-card rounded-lg p-3">
                    <div className="text-[10px] font-mono text-on-surface/40">{timeAgo(fb.timestamp as string)}</div>
                    <div className="text-xs text-on-surface mt-1 truncate">{(fb.user_message as string || "").slice(0, 60)}</div>
                    {fb.comment ? <div className="text-xs text-primary italic mt-1">{String(fb.comment)}</div> : null}
                    {fb.structured_data && (fb.structured_data as Record<string, Record<string, number>>)?.valuation?.fmv_low ? (
                      <div className="text-[10px] font-mono text-secondary mt-1">
                        FMV: {formatPrice((fb.structured_data as Record<string, Record<string, number>>).valuation.fmv_low)} - {formatPrice((fb.structured_data as Record<string, Record<string, number>>).valuation.fmv_high)}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Actions</h3>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleExportLog}
                className="px-4 py-2 rounded-lg bg-white/[0.06] border border-white/10 text-xs font-mono text-on-surface/60 hover:text-white hover:bg-white/10 transition-all"
              >
                Export valuation log
              </button>
              <button
                onClick={handleClearHistory}
                className="px-4 py-2 rounded-lg bg-white/[0.06] border border-white/10 text-xs font-mono text-on-surface/60 hover:text-white hover:bg-white/10 transition-all"
              >
                Clear conversation history
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
