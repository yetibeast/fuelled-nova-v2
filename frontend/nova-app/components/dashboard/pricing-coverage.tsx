"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  fetchFuelledCoverage,
  downloadFuelledReport,
  startFuelledPriceBatch,
  pollFuelledPriceStatus,
  uploadFuelledPrices,
} from "@/lib/api";
import { MaterialIcon } from "@/components/ui/material-icon";

interface CoverageData {
  total: number;
  asking_price_count: number;
  asking_price_pct: number;
  valued_count: number;
  valued_pct: number;
  ai_only_count: number;
  unpriced: number;
  by_tier: Record<string, number>;
  by_category: { category: string; count: number }[];
  completeness_avg: number;
}

interface BatchJob {
  status: string;
  job_id?: string;
  total?: number;
  completed?: number;
  succeeded?: number;
  failed?: number;
  current_item?: string | null;
  finished_at?: string | null;
}

const TIER_CONFIG = [
  { key: "tier_1", label: "High", tier: 1, color: "#10b981", desc: "Make + Model + Year" },
  { key: "tier_2", label: "Medium", tier: 2, color: "#f59e0b", desc: "Make + Year" },
  { key: "tier_3", label: "Low", tier: 3, color: "#EF5D28", desc: "Make only" },
  { key: "tier_4", label: "Very Low", tier: 4, color: "#ef4444", desc: "Category only" },
];

/** Bar color based on coverage % — red/orange when low, amber mid, green when close to target. */
function progressColor(pct: number): string {
  if (pct >= 75) return "#10b981"; // emerald
  if (pct >= 50) return "#f59e0b"; // amber
  if (pct >= 30) return "#EF5D28"; // primary orange
  return "#ef4444"; // red
}

export function PricingCoverage() {
  const [data, setData] = useState<CoverageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [downloading, setDownloading] = useState(false);
  const [batchJob, setBatchJob] = useState<BatchJob | null>(null);
  const [batchStarting, setBatchStarting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{ updated: number; total_rows: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load coverage data on mount
  useEffect(() => {
    fetchFuelledCoverage()
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });

    // Also check if a batch job is already running
    pollFuelledPriceStatus()
      .then((s) => {
        if (s.status === "running") {
          setBatchJob(s);
          startPolling();
        }
      })
      .catch(() => {
        /* ignore */
      });

    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const s = await pollFuelledPriceStatus();
        setBatchJob(s);
        if (s.status !== "running") {
          stopPolling();
          // Refresh coverage data after batch completes
          fetchFuelledCoverage()
            .then((d) => setData(d))
            .catch(() => {
              /* ignore */
            });
        }
      } catch {
        /* ignore */
      }
    }, 2000);
  }, [stopPolling]);

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadFuelledReport();
    } catch {
      /* ignore */
    } finally {
      setDownloading(false);
    }
  }

  async function handleBatchPrice() {
    setBatchStarting(true);
    try {
      const result = await startFuelledPriceBatch([1, 2], 50);
      if (result.job_id) {
        setBatchJob({
          status: "running",
          job_id: result.job_id,
          total: result.total,
          completed: 0,
          succeeded: 0,
          failed: 0,
          current_item: null,
        });
        startPolling();
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed";
      alert(msg);
    } finally {
      setBatchStarting(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const result = await uploadFuelledPrices(file);
      setUploadResult(result);
      // Refresh coverage stats
      fetchFuelledCoverage().then(setData).catch(() => {});
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      alert(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="glass-card rounded-xl p-6 mb-6">
        <div className="h-5 w-56 bg-white/[0.06] rounded animate-pulse mb-4" />
        <div className="h-5 w-full bg-white/[0.06] rounded-full animate-pulse mb-3" />
        <div className="grid grid-cols-4 gap-4 mb-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 bg-white/[0.06] rounded animate-pulse" />
          ))}
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-4 bg-white/[0.06] rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-2">
          Fuelled Pricing Coverage
        </h3>
        <p className="text-xs text-on-surface/40 font-mono">
          Coverage endpoint not available
        </p>
      </div>
    );
  }

  const tierMax = Math.max(
    ...TIER_CONFIG.map((t) => data.by_tier[t.key] || 0),
    1
  );

  const batchRunning = batchJob?.status === "running";
  const batchComplete = batchJob?.status === "completed";

  return (
    <div className="glass-card rounded-xl p-6 mb-6">
      {/* Header + big percentage */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline font-bold text-sm tracking-tight">
          Fuelled Pricing Coverage
        </h3>
        <span className="text-2xl font-bold font-mono text-on-surface">
          {data.valued_pct}
          <span className="text-sm text-on-surface/40">%</span>
        </span>
      </div>

      {/* Progress bar — color reflects how close to target */}
      <div className="h-5 rounded-full bg-white/[0.04] overflow-hidden mb-1">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${data.valued_pct}%`,
            backgroundColor: progressColor(data.valued_pct),
          }}
        />
      </div>
      <p className="text-[10px] font-mono text-on-surface/30 mb-5">
        Asking price (public): {data.asking_price_pct}%
      </p>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-5">
        <div className="text-center">
          <p className="text-[10px] font-mono text-on-surface/30 uppercase tracking-wider">
            Total
          </p>
          <p className="text-lg font-bold font-mono text-on-surface">
            {data.total.toLocaleString()}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-mono text-on-surface/30 uppercase tracking-wider">
            Listed Price
          </p>
          <p className="text-lg font-bold font-mono text-on-surface">
            {data.asking_price_count.toLocaleString()}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-mono text-on-surface/30 uppercase tracking-wider">
            Unvalued
          </p>
          <p className="text-lg font-bold font-mono text-primary">
            {data.unpriced.toLocaleString()}
          </p>
        </div>
        <div className="text-center">
          <p className="text-[10px] font-mono text-on-surface/30 uppercase tracking-wider">
            AI Priced
          </p>
          <p className="text-lg font-bold font-mono text-on-surface">
            {data.ai_only_count.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Pricability tier breakdown */}
      <div className="mb-4">
        <p className="text-[10px] font-mono text-on-surface/40 uppercase tracking-wider mb-3">
          Pricability Tiers (Unvalued)
        </p>
        <div className="space-y-2">
          {TIER_CONFIG.map((t) => {
            const count = data.by_tier[t.key] || 0;
            const pct = tierMax > 0 ? (count / tierMax) * 100 : 0;
            return (
              <div key={t.key} className="flex items-center gap-3">
                <span className="text-[10px] font-mono text-on-surface/40 w-24 shrink-0">
                  Tier {t.tier} — {t.label}
                </span>
                <div className="flex-1 h-3 rounded-full bg-white/[0.04] overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: t.color,
                    }}
                  />
                </div>
                <span className="text-xs font-mono text-on-surface/60 w-12 text-right">
                  {count.toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tier legend */}
      <div className="mb-4 pt-2 border-t border-white/[0.04]">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {TIER_CONFIG.map((t) => (
            <p key={t.key} className="text-[10px] font-mono text-on-surface/25">
              <span style={{ color: t.color }}>Tier {t.tier}</span> = {t.desc}
            </p>
          ))}
        </div>
      </div>

      {/* Data completeness */}
      <p className="text-[10px] font-mono text-on-surface/30 mb-4">
        AVG DATA COMPLETENESS: {data.completeness_avg}%
      </p>

      {/* Batch progress (conditional) */}
      {batchRunning && batchJob && (
        <div className="mb-4 p-3 rounded-lg bg-white/[0.04] border border-white/[0.06]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-on-surface/60 flex items-center gap-2">
              <MaterialIcon icon="autorenew" className="text-[16px] animate-spin text-primary" />
              Pricing {batchJob.completed || 0} of {batchJob.total || 0}...
            </span>
            <span className="text-[10px] font-mono text-on-surface/30">
              {batchJob.succeeded || 0} OK / {batchJob.failed || 0} failed
            </span>
          </div>
          <div className="h-2 rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{
                width: `${
                  batchJob.total
                    ? ((batchJob.completed || 0) / batchJob.total) * 100
                    : 0
                }%`,
              }}
            />
          </div>
          {batchJob.current_item && (
            <p className="text-[10px] font-mono text-on-surface/30 mt-1 truncate">
              {batchJob.current_item}
            </p>
          )}
        </div>
      )}

      {batchComplete && batchJob && (
        <div className="mb-4 p-3 rounded-lg border border-emerald-500/20" style={{ background: "rgba(16, 185, 129, 0.06)" }}>
          <div className="flex items-center gap-2">
            <MaterialIcon icon="check_circle" className="text-[16px] text-emerald-400" />
            <span className="text-xs font-mono text-emerald-400">
              Batch complete: {batchJob.succeeded || 0} priced, {batchJob.failed || 0} failed
            </span>
          </div>
        </div>
      )}

      {uploadResult && (
        <div className="mb-4 p-3 rounded-lg border border-emerald-500/20" style={{ background: "rgba(16, 185, 129, 0.06)" }}>
          <div className="flex items-center gap-2">
            <MaterialIcon icon="check_circle" className="text-[16px] text-emerald-400" />
            <span className="text-xs font-mono text-emerald-400">
              Import complete: {uploadResult.updated} listings updated from {uploadResult.total_rows} rows
            </span>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        onChange={handleUpload}
        className="hidden"
      />
      <div className="flex gap-3">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="px-4 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-on-surface/60 hover:bg-white/[0.08] transition-all flex items-center gap-2 disabled:opacity-40"
        >
          <MaterialIcon icon="download" className="text-[16px]" />
          {downloading ? "Generating..." : "Download Report"}
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-on-surface/60 hover:bg-white/[0.08] transition-all flex items-center gap-2 disabled:opacity-40"
        >
          <MaterialIcon icon="upload" className="text-[16px]" />
          {uploading ? "Importing..." : "Upload Prices"}
        </button>
        <button
          onClick={handleBatchPrice}
          disabled={batchStarting || batchRunning}
          className="px-4 py-2 rounded-lg bg-primary/10 border border-primary/20 text-xs font-mono text-primary hover:bg-primary/20 transition-all flex items-center gap-2 disabled:opacity-40"
        >
          <MaterialIcon icon="auto_fix_high" className="text-[16px]" />
          {batchStarting
            ? "Starting..."
            : batchRunning
              ? "Running..."
              : "Price Tier 1 & 2"}
        </button>
      </div>
    </div>
  );
}
