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
  { tier: 1, label: "One-Pager", desc: "1 page" },
  { tier: 2, label: "Valuation Support", desc: "5-6 pages" },
  { tier: 3, label: "Full Assessment", desc: "10+ pages" },
];

export function ExportButton({
  structuredData,
  responseText,
  userMessage,
  batchData,
}: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
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

  async function handleTierSelect(tier: number) {
    setOpen(false);
    if (loading) return;
    setLoading(true);
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
    }
  }

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
                <div className="text-[10px] font-mono text-on-surface/40">{t.desc}</div>
              </div>
              <MaterialIcon icon="chevron_right" className="text-sm text-on-surface/30" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
