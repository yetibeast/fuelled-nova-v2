"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { ConfidencePill } from "@/components/ui/confidence-pill";
import { fetchAdminValuations } from "@/lib/api";
import { timeAgo, formatFmvRange } from "@/lib/utils";

interface Valuation {
  timestamp: string;
  user_id?: string | null;
  user_email?: string | null;
  user_message: string;
  tools_used: string[];
  confidence: string;
  fmv_low: number | null;
  fmv_mid: number | null;
  fmv_high: number | null;
  response_length: number | null;
}

export function ValuationsTab() {
  const [entries, setEntries] = useState<Valuation[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminValuations()
      .then((data: Valuation[]) => setEntries(data))
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="text-red-400 font-mono text-xs">Error: {error}</div>;

  return (
    <DataTable
      title="Valuation Log"
      badge={`${entries.length} VALUATIONS`}
      headers={["TIME", "USER", "QUERY", "FMV RANGE", "CONFIDENCE", "TOOLS"]}
    >
      {entries.map((v, i) => {
        const isExpanded = expanded === i;
        const fmvRange = formatFmvRange(v.fmv_low, v.fmv_high);
        // Show email's local-part by default; full email when expanded.
        const userLabel = v.user_email
          ? (isExpanded ? v.user_email : v.user_email.split("@")[0])
          : null;
        return (
          <tr
            key={i}
            onClick={() => setExpanded(isExpanded ? null : i)}
            className="cursor-pointer hover:bg-white/[0.04] transition-colors"
          >
            <td className="px-6 py-3 text-on-surface/50">{v.timestamp ? timeAgo(v.timestamp) : "---"}</td>
            <td className="px-6 py-3 text-on-surface/70">
              {userLabel ?? <span className="text-on-surface/30">—</span>}
            </td>
            <td className="px-6 py-3 text-on-surface font-medium">
              {isExpanded ? v.user_message : (v.user_message || "").slice(0, 50) + (v.user_message && v.user_message.length > 50 ? "..." : "")}
            </td>
            <td className="px-6 py-3 text-on-surface/70">{fmvRange}</td>
            <td className="px-6 py-3">{v.confidence ? <ConfidencePill level={v.confidence} /> : "---"}</td>
            <td className="px-6 py-3 text-on-surface/50">
              {v.tools_used.length}
              {isExpanded && v.tools_used.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {v.tools_used.map((t, j) => (
                    <span key={j} className="px-1.5 py-0.5 rounded bg-white/[0.06] text-[9px] font-mono text-on-surface/40">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </td>
          </tr>
        );
      })}
    </DataTable>
  );
}
