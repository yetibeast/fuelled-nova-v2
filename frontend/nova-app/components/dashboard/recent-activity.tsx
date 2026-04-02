"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { ConfidencePill } from "@/components/ui/confidence-pill";
import { fetchRecentValuations } from "@/lib/api";
import { timeAgo, formatPrice } from "@/lib/utils";

interface Valuation {
  timestamp: string;
  user_message?: string;
  fmv_low?: number;
  fmv_high?: number;
  confidence?: string;
}

export function RecentActivity() {
  const [rows, setRows] = useState<Valuation[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchRecentValuations()
      .then((data: Valuation[]) => setRows(data.slice(0, 5)))
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <DataTable title="Recent Valuations" badge="LAST 5" headers={["TIME", "EQUIPMENT", "FMV RANGE", "CONFIDENCE"]} headerAligns={["left", "left", "right", "left"]}>
        <tr><td colSpan={4} className="px-6 py-6 text-center text-on-surface/30 text-xs font-mono">Unable to load recent valuations</td></tr>
      </DataTable>
    );
  }

  return (
    <DataTable
      title="Recent Valuations"
      badge="LAST 5"
      headers={["TIME", "EQUIPMENT", "FMV RANGE", "CONFIDENCE"]}
      headerAligns={["left", "left", "right", "left"]}
    >
      {rows.map((v, i) => (
        <tr key={i} className="hover:bg-white/[0.04] transition-colors">
          <td className="px-6 py-3 text-on-surface/50">{timeAgo(v.timestamp)}</td>
          <td className="px-6 py-3 text-on-surface">{v.user_message || "---"}</td>
          <td className="px-6 py-3 text-right text-secondary font-bold">
            {v.fmv_low ? `${formatPrice(v.fmv_low)} - ${formatPrice(v.fmv_high)}` : "---"}
          </td>
          <td className="px-6 py-3">
            <ConfidencePill level={v.confidence || "LOW"} />
          </td>
        </tr>
      ))}
    </DataTable>
  );
}
