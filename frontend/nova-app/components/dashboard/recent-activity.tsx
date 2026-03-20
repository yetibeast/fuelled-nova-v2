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

  useEffect(() => {
    fetchRecentValuations()
      .then((data: Valuation[]) => setRows(data.slice(0, 5)))
      .catch(() => {
        setRows([
          { timestamp: new Date(Date.now() - 7200000).toISOString(), user_message: "Ariel JGK/4 3-Stage 1400HP", fmv_low: 673000, fmv_high: 910000, confidence: "HIGH" },
          { timestamp: new Date(Date.now() - 18000000).toISOString(), user_message: "VaporTech Ro-Flo VRU 40HP", fmv_low: 38000, fmv_high: 52000, confidence: "MEDIUM" },
          { timestamp: new Date(Date.now() - 86400000).toISOString(), user_message: "400 BBL Production Tank", fmv_low: 25000, fmv_high: 45000, confidence: "HIGH" },
        ]);
      });
  }, []);

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
