"use client";

import { useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { MaterialIcon } from "@/components/ui/material-icon";
import {
  triggerScraperRun,
  pauseScraper,
  resumeScraper,
  updateScraper,
  deleteScraper,
  fetchScraperRuns,
} from "@/lib/api";
import { timeAgo } from "@/lib/utils";

export interface ScraperTarget {
  id: string;
  name: string;
  url: string | null;
  status: string;
  scraper_type: string;
  schedule_cron: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  health_pct: number;
  total_items: number;
  items_with_price: number;
}

interface RunEntry {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  items_found: number;
  items_new: number;
  items_updated: number;
  error_message: string | null;
  duration_ms: number | null;
}

function cronToHuman(cron: string | null): string {
  if (!cron) return "Manual";
  if (cron === "0 */6 * * *") return "Every 6h";
  if (cron === "0 */12 * * *") return "Every 12h";
  if (cron === "0 0 * * *") return "Daily midnight";
  if (cron === "0 2 * * *") return "Daily 2 AM";
  if (cron.startsWith("0 */")) {
    const h = cron.split(" ")[1]?.replace("*/", "");
    return `Every ${h}h`;
  }
  return cron;
}

function healthDotClass(pct: number): string {
  if (pct >= 80) return "status-green";
  if (pct >= 50) return "status-yellow";
  return "status-red";
}

function healthLabel(pct: number): string {
  if (pct >= 80) return "Healthy";
  if (pct >= 50) return "Degraded";
  return "Error";
}

function formatDuration(ms: number | null): string {
  if (ms == null) return "---";
  if (ms < 1000) return ms + "ms";
  if (ms < 60000) return (ms / 1000).toFixed(1) + "s";
  return Math.floor(ms / 60000) + "m " + Math.round((ms % 60000) / 1000) + "s";
}

function runStatusColor(s: string): string {
  if (s === "success") return "text-emerald-400";
  if (s === "partial") return "text-amber-400";
  if (s === "failed") return "text-red-400";
  return "text-on-surface/50";
}

interface Props {
  scrapers: ScraperTarget[];
  onRefresh: () => void;
}

export function ScraperTable({ scrapers, onRefresh }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunEntry[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [editCron, setEditCron] = useState<string | null>(null);
  const [cronValue, setCronValue] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  async function handleExpand(id: string) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    setRunsLoading(true);
    try {
      const data = await fetchScraperRuns(id);
      setRuns(Array.isArray(data) ? data.slice(0, 5) : []);
    } catch {
      setRuns([]);
    }
    setRunsLoading(false);
  }

  async function handleRunNow(id: string) {
    setActionLoading(id + "-run");
    try {
      await triggerScraperRun(id);
      onRefresh();
    } catch { /* silently fail */ }
    setActionLoading(null);
  }

  async function handleTogglePause(s: ScraperTarget) {
    setActionLoading(s.id + "-pause");
    try {
      if (s.status === "paused") {
        await resumeScraper(s.id);
      } else {
        await pauseScraper(s.id);
      }
      onRefresh();
    } catch { /* silently fail */ }
    setActionLoading(null);
  }

  async function handleDelete(id: string) {
    if (!confirm("Remove this scraper target? Existing listings will not be deleted.")) return;
    setActionLoading(id + "-del");
    try {
      await deleteScraper(id);
      onRefresh();
    } catch { /* silently fail */ }
    setActionLoading(null);
  }

  async function handleSaveCron(id: string) {
    try {
      await updateScraper(id, { schedule_cron: cronValue || null });
      setEditCron(null);
      onRefresh();
    } catch { /* silently fail */ }
  }

  return (
    <DataTable
      title="Scraper Targets"
      badge={`${scrapers.length} SOURCES`}
      headers={["SOURCE", "TYPE", "LISTINGS", "WITH PRICE", "SCHEDULE", "LAST RUN", "STATUS", "ACTIONS"]}
      headerAligns={["left", "left", "right", "right", "left", "left", "left", "left"]}
      footer={
        <span className="text-on-surface/30 text-xs font-mono">
          Click a row to see run history and details
        </span>
      }
    >
      {scrapers.map((s) => {
        const isExpanded = expanded === s.id;
        return (
          <tr key={s.id} className="group">
            {/* Source name - clickable to expand */}
            <td className="px-6 py-3">
              <button
                onClick={() => handleExpand(s.id)}
                className="text-on-surface font-medium hover:text-primary transition-colors text-left flex items-center gap-2"
              >
                <MaterialIcon
                  icon={isExpanded ? "expand_less" : "expand_more"}
                  className="text-[14px] text-on-surface/30"
                />
                {s.name}
              </button>
            </td>

            {/* Type badge */}
            <td className="px-6 py-3">
              <span className="bg-white/[0.06] text-[10px] font-mono px-2 py-0.5 rounded text-on-surface/60">
                {s.scraper_type}
              </span>
            </td>

            {/* Listings */}
            <td className="px-6 py-3 text-right text-on-surface/70">
              {s.total_items.toLocaleString()}
            </td>

            {/* With price */}
            <td className="px-6 py-3 text-right text-secondary">
              {s.items_with_price.toLocaleString()}
            </td>

            {/* Schedule */}
            <td className="px-6 py-3 text-on-surface/50">
              {cronToHuman(s.schedule_cron)}
            </td>

            {/* Last run */}
            <td className="px-6 py-3 text-on-surface/50">
              {s.last_run_at ? timeAgo(s.last_run_at) : "Never"}
            </td>

            {/* Status */}
            <td className="px-6 py-3">
              <span className="flex items-center gap-2">
                <span className={`status-dot ${s.status === "paused" ? "status-yellow" : healthDotClass(s.health_pct)}`} />
                <span className="text-on-surface/50">
                  {s.status === "paused" ? "Paused" : healthLabel(s.health_pct)}
                </span>
              </span>
            </td>

            {/* Actions */}
            <td className="px-6 py-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleRunNow(s.id)}
                  disabled={actionLoading === s.id + "-run"}
                  className="text-[10px] font-mono text-primary hover:text-primary/80 disabled:opacity-40"
                >
                  {actionLoading === s.id + "-run" ? "..." : "Run Now"}
                </button>
                <button
                  onClick={() => handleTogglePause(s)}
                  disabled={actionLoading === s.id + "-pause"}
                  className="text-on-surface/30 hover:text-on-surface/70"
                >
                  <MaterialIcon
                    icon={s.status === "paused" ? "play_arrow" : "pause"}
                    className="text-[16px]"
                  />
                </button>
                <button
                  onClick={() => handleDelete(s.id)}
                  disabled={actionLoading === s.id + "-del"}
                  className="text-on-surface/30 hover:text-red-400"
                >
                  <MaterialIcon icon="delete" className="text-[16px]" />
                </button>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="mt-3 p-4 rounded-lg bg-white/[0.03] border border-white/[0.06] space-y-4">
                  {/* Target info */}
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px] font-mono">
                    <div>
                      <span className="text-on-surface/30">URL</span>
                      <div className="text-on-surface/70 truncate">{s.url || "---"}</div>
                    </div>
                    <div>
                      <span className="text-on-surface/30">Cron</span>
                      <div className="text-on-surface/70">{s.schedule_cron || "manual"}</div>
                    </div>
                    <div>
                      <span className="text-on-surface/30">Health</span>
                      <div className="text-on-surface/70">{s.health_pct}%</div>
                    </div>
                    <div>
                      <span className="text-on-surface/30">Type</span>
                      <div className="text-on-surface/70">{s.scraper_type}</div>
                    </div>
                  </div>

                  {/* Inline schedule edit */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-on-surface/30">Schedule:</span>
                    {editCron === s.id ? (
                      <>
                        <input
                          className="recessed-input rounded px-2 py-1 text-xs text-on-surface w-36 font-mono"
                          value={cronValue}
                          onChange={(e) => setCronValue(e.target.value)}
                          placeholder="0 */6 * * *"
                        />
                        <button
                          onClick={() => handleSaveCron(s.id)}
                          className="text-emerald-400 hover:text-emerald-300"
                        >
                          <MaterialIcon icon="check" className="text-[16px]" />
                        </button>
                        <button
                          onClick={() => setEditCron(null)}
                          className="text-on-surface/40 hover:text-on-surface/70"
                        >
                          <MaterialIcon icon="close" className="text-[16px]" />
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => { setEditCron(s.id); setCronValue(s.schedule_cron || ""); }}
                        className="text-[10px] font-mono text-primary hover:text-primary/80"
                      >
                        Edit
                      </button>
                    )}
                  </div>

                  {/* Run history */}
                  <div>
                    <div className="text-[10px] font-mono text-on-surface/30 uppercase tracking-widest mb-2">
                      Recent Runs
                    </div>
                    {runsLoading ? (
                      <div className="space-y-2">
                        {[1, 2, 3].map((i) => (
                          <div key={i} className="h-6 bg-white/[0.04] rounded animate-pulse" />
                        ))}
                      </div>
                    ) : runs.length === 0 ? (
                      <div className="text-[11px] font-mono text-on-surface/20">No runs recorded</div>
                    ) : (
                      <table className="w-full text-[11px] font-mono">
                        <thead className="text-on-surface/20">
                          <tr>
                            <th className="text-left py-1 pr-3">DATE</th>
                            <th className="text-right py-1 pr-3">FOUND</th>
                            <th className="text-right py-1 pr-3">NEW</th>
                            <th className="text-right py-1 pr-3">UPDATED</th>
                            <th className="text-left py-1 pr-3">STATUS</th>
                            <th className="text-right py-1 pr-3">DURATION</th>
                            <th className="text-left py-1">ERROR</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.03]">
                          {runs.map((r) => (
                            <tr key={r.id}>
                              <td className="py-1 pr-3 text-on-surface/50">
                                {r.started_at ? timeAgo(r.started_at) : "---"}
                              </td>
                              <td className="py-1 pr-3 text-right text-on-surface/70">{r.items_found}</td>
                              <td className="py-1 pr-3 text-right text-secondary">{r.items_new}</td>
                              <td className="py-1 pr-3 text-right text-on-surface/50">{r.items_updated}</td>
                              <td className={`py-1 pr-3 ${runStatusColor(r.status)}`}>{r.status}</td>
                              <td className="py-1 pr-3 text-right text-on-surface/40">
                                {formatDuration(r.duration_ms)}
                              </td>
                              <td className="py-1 text-red-400/70 truncate max-w-[120px]">
                                {r.error_message || "---"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              )}
            </td>
          </tr>
        );
      })}
    </DataTable>
  );
}
