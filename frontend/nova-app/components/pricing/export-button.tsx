"use client";

import { useState, useRef, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { generateTieredReport } from "@/lib/api";

interface ExportButtonProps {
  structuredData: Record<string, unknown>;
  responseText: string;
  userMessage: string;
  batchData?: { results: Record<string, unknown>[]; summary: Record<string, unknown> };
}

const TIERS = [
  { tier: 1, label: "One-Pager", desc: "1 page", time: "Instant" },
  { tier: 2, label: "Valuation Support", desc: "5-6 pages", time: "~30 seconds" },
  { tier: 3, label: "Full Assessment", desc: "10+ pages", time: "~45 seconds" },
];

export function ExportButton({
  structuredData,
  responseText,
  userMessage,
  batchData,
}: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [loadingTier, setLoadingTier] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
      return () => { if (timerRef.current) clearInterval(timerRef.current); };
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setElapsed(0);
    }
  }, [loading]);

  async function handleTierSelect(tier: number) {
    setOpen(false);
    if (loading) return;
    setLoading(true);
    setLoadingTier(tier);
    try {
      const isBatch = !!batchData;
      const type = isBatch ? "portfolio" : "single";
      const data = isBatch
        ? { results: batchData!.results, summary: batchData!.summary }
        : { structured: structuredData, response_text: responseText, user_message: userMessage };

      const blob = await generateTieredReport(tier, type, data as Record<string, unknown>);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const tierLabel = TIERS.find((t) => t.tier === tier)?.label ?? "Report";
      a.download = `Fuelled_${tierLabel.replace(/\s+/g, "_")}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to generate report. Please try again.");
    } finally {
      setLoading(false);
      setLoadingTier(null);
    }
  }

  const tierInfo = TIERS.find((t) => t.tier === loadingTier);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        disabled={loading}
        className={`flex items-center gap-3 bg-white/8 border border-primary/25 text-primary/80 rounded-full py-2.5 px-8 hover:bg-white/12 hover:text-primary transition-all group ${
          loading ? "opacity-50 cursor-wait" : ""
        }`}
      >
        <MaterialIcon
          icon="description"
          className="text-xl group-hover:rotate-12 transition-transform"
        />
        <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-bold">
          {loading ? "Generating..." : "Export Report"}
        </span>
        <MaterialIcon
          icon="expand_less"
          className={`text-base transition-transform ${open ? "" : "rotate-180"}`}
        />
      </button>

      {/* Tier selection dropdown */}
      {open && (
        <div className="absolute bottom-full left-0 mb-2 w-64 glass-card rounded-xl border border-white/10 overflow-hidden z-50">
          {TIERS.map((t) => (
            <button
              key={t.tier}
              onClick={() => handleTierSelect(t.tier)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.06] transition-colors text-left"
            >
              <div>
                <div className="text-xs font-medium text-on-surface/90">{t.label}</div>
                <div className="text-[10px] font-mono text-on-surface/40">{t.desc} &middot; {t.time}</div>
              </div>
              <MaterialIcon icon="chevron_right" className="text-sm text-on-surface/30" />
            </button>
          ))}
        </div>
      )}

      {/* Generating overlay */}
      {loading && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="glass-card rounded-2xl border border-white/10 p-8 max-w-sm w-full mx-4 text-center space-y-4">
            {/* Spinner */}
            <div className="w-14 h-14 mx-auto rounded-full border-[3px] border-primary/20 border-t-primary animate-spin" />

            <div>
              <h3 className="font-headline font-bold text-base text-on-surface">
                Generating {tierInfo?.label || "Report"}
              </h3>
              <p className="text-on-surface/50 text-xs font-mono mt-1">
                {loadingTier === 1
                  ? "Building document..."
                  : "AI is writing equipment-specific analysis..."}
              </p>
            </div>

            {/* Progress bar (estimated) */}
            {loadingTier && loadingTier > 1 && (
              <div className="space-y-1">
                <div className="w-full h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary/70 rounded-full transition-all duration-1000 ease-linear"
                    style={{ width: `${Math.min(elapsed / (loadingTier === 2 ? 35 : 50) * 100, 95)}%` }}
                  />
                </div>
                <p className="text-on-surface/30 text-[10px] font-mono">
                  {elapsed}s elapsed &middot; typically {tierInfo?.time}
                </p>
              </div>
            )}

            <p className="text-on-surface/30 text-[10px]">
              Your download will start automatically
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
