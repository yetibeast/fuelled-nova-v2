"use client";

import { formatPrice, formatRcn, confidenceColor } from "@/lib/utils";

interface Factor {
  label: string;
  value: number | string;
}

interface ValuationData {
  fmv_low: number;
  fmv_high: number;
  confidence: string;
  rcn?: number;
  factors?: Factor[];
}

interface ValuationCardProps {
  data: ValuationData;
}

export function ValuationCard({ data }: ValuationCardProps) {
  const confColor = confidenceColor(data.confidence);

  return (
    <div className="glass-card p-8 rounded-xl w-full border-l-4 border-l-primary">
      <div className="flex flex-col md:flex-row justify-between items-start gap-6">
        {/* Left: FMV */}
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-secondary font-mono text-[10px] uppercase tracking-[0.2em]">
              Estimated Fair Market Value
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <h2 className="text-4xl font-headline font-bold text-white tracking-tight">
              {formatPrice(data.fmv_low)} - {formatPrice(data.fmv_high)}
            </h2>
            <span className="font-mono text-sm text-secondary">CAD</span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span
              className="px-2 py-0.5 rounded text-[10px] font-mono font-bold"
              style={{
                background: confColor + "1a",
                color: confColor,
              }}
            >
              {data.confidence} CONFIDENCE
            </span>
          </div>
        </div>

        {/* Right: RCN */}
        {data.rcn != null && (
          <div className="flex flex-col items-end gap-2 text-right">
            <span className="text-on-surface/60 font-mono text-[10px] uppercase tracking-widest">
              Est. Replacement Cost (RCN)
            </span>
            <span className="text-2xl font-mono text-primary font-bold tracking-tighter">
              {formatRcn(data.rcn)}{" "}
              <span className="text-sm font-normal">CAD</span>
            </span>
          </div>
        )}
      </div>

      {/* Factor multipliers */}
      {data.factors && data.factors.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-6 border-t border-white/5">
          {data.factors.map((f, i) => {
            const display =
              typeof f.value === "number" && f.value <= 5
                ? f.value.toFixed(2) + "x"
                : String(f.value);
            return (
              <div key={i} className="flex flex-col">
                <span className="text-[10px] text-on-surface/40 uppercase tracking-widest mb-1">
                  {f.label}
                </span>
                <span className="font-mono text-lg text-secondary">
                  {display}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
