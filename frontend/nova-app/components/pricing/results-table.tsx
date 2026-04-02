"use client";

import { formatPrice, confidenceColor } from "@/lib/utils";
import { MaterialIcon } from "@/components/ui/material-icon";

interface BatchResult {
  title: string;
  structured: {
    valuation?: {
      fmv_low?: number;
      fmv_high?: number;
      confidence?: string;
      currency?: string;
    };
    comparables?: Array<Record<string, unknown>>;
  };
  confidence?: string;
}

interface BatchProgress {
  completed: number;
  total: number;
  current_item?: string;
}

interface ResultsTableProps {
  results: BatchResult[];
  summary?: { total_fmv_low?: number; total_fmv_high?: number };
  isLoading?: boolean;
  progress?: BatchProgress;
  onSelectItem: (index: number) => void;
}

export function ResultsTable({
  results,
  summary,
  isLoading,
  progress,
  onSelectItem,
}: ResultsTableProps) {
  const completedCount = results.length;
  const totalCount = progress?.total ?? completedCount;

  return (
    <div className="glass-card overflow-hidden rounded-xl">
      {/* Header */}
      <div className="px-6 py-4 bg-white/5 border-b border-white/5 flex justify-between items-center">
        <h3 className="font-headline font-bold text-sm tracking-tight text-on-surface">
          Portfolio Results
        </h3>
        <span className="text-[10px] font-mono text-secondary">
          {completedCount} OF {totalCount} ITEMS
        </span>
      </div>

      {/* Loading progress */}
      {isLoading && progress && (
        <div className="px-6 py-3 border-b border-white/5 bg-white/[0.02]">
          <div className="flex items-center gap-3 mb-2">
            <MaterialIcon
              icon="autorenew"
              className="text-sm text-secondary animate-spin"
            />
            <span className="text-xs text-on-surface/70">
              Pricing item {progress.completed + 1} of {progress.total}
              {progress.current_item ? ` \u2014 ${progress.current_item}` : ""}
            </span>
          </div>
          <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500"
              style={{
                width: `${totalCount > 0 ? (progress.completed / totalCount) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="text-on-surface/40 border-b border-white/5">
            <tr>
              <th className="px-6 py-3 font-medium w-10">#</th>
              <th className="px-6 py-3 font-medium">EQUIPMENT</th>
              <th className="px-6 py-3 font-medium text-right">FMV RANGE</th>
              <th className="px-6 py-3 font-medium text-center">CONFIDENCE</th>
              <th className="px-6 py-3 font-medium text-center">COMPS</th>
              <th className="px-6 py-3 font-medium text-center">VIEW</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {results.map((r, i) => {
              const val = r.structured?.valuation;
              const conf = val?.confidence || r.confidence || "LOW";
              const confColor = confidenceColor(conf);
              const compsCount = r.structured?.comparables?.length ?? 0;

              return (
                <tr
                  key={i}
                  className="hover:bg-white/10 transition-colors"
                >
                  <td className="px-6 py-4 text-on-surface/40">{i + 1}</td>
                  <td className="px-6 py-4 text-on-surface font-medium max-w-[200px] truncate">
                    {r.title}
                  </td>
                  <td className="px-6 py-4 text-right text-secondary font-bold whitespace-nowrap">
                    {val?.fmv_low != null && val?.fmv_high != null
                      ? `${formatPrice(val.fmv_low)} \u2013 ${formatPrice(val.fmv_high)}`
                      : "---"}
                    {val?.currency && (
                      <span className="text-on-surface/40 font-normal ml-1">
                        {val.currency}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-bold"
                      style={{
                        background: confColor + "1a",
                        color: confColor,
                      }}
                    >
                      {conf}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center text-on-surface/70">
                    {compsCount}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => onSelectItem(i)}
                      className="text-secondary hover:text-primary transition-colors"
                    >
                      <MaterialIcon icon="visibility" className="text-base" />
                    </button>
                  </td>
                </tr>
              );
            })}

            {/* Loading row for current item */}
            {isLoading && progress && progress.completed < progress.total && (
              <tr className="opacity-50">
                <td className="px-6 py-4 text-on-surface/40">
                  {completedCount + 1}
                </td>
                <td className="px-6 py-4 text-on-surface/50 italic">
                  {progress.current_item || "Processing..."}
                </td>
                <td className="px-6 py-4 text-right text-on-surface/30">---</td>
                <td className="px-6 py-4 text-center text-on-surface/30">---</td>
                <td className="px-6 py-4 text-center text-on-surface/30">---</td>
                <td className="px-6 py-4 text-center text-on-surface/30">
                  <MaterialIcon
                    icon="autorenew"
                    className="text-base animate-spin"
                  />
                </td>
              </tr>
            )}
          </tbody>

          {/* Summary footer */}
          {summary &&
            summary.total_fmv_low != null &&
            summary.total_fmv_high != null && (
              <tfoot className="border-t border-white/10">
                <tr className="bg-white/[0.03]">
                  <td className="px-6 py-4" />
                  <td className="px-6 py-4 text-on-surface font-bold text-xs">
                    PORTFOLIO TOTAL
                  </td>
                  <td className="px-6 py-4 text-right text-primary font-bold whitespace-nowrap">
                    {formatPrice(summary.total_fmv_low)} &ndash;{" "}
                    {formatPrice(summary.total_fmv_high)}
                  </td>
                  <td className="px-6 py-4" />
                  <td className="px-6 py-4" />
                  <td className="px-6 py-4" />
                </tr>
              </tfoot>
            )}
        </table>
      </div>
    </div>
  );
}
