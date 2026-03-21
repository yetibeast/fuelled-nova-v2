"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { fetchAdminFeedback } from "@/lib/api";
import { timeAgo, formatFmvRange } from "@/lib/utils";

interface FeedbackEntry {
  timestamp: string;
  rating: string;
  comment: string | null;
  user_message: string;
  fmv_low: number | null;
  fmv_mid: number | null;
  fmv_high: number | null;
}

export function FeedbackTab() {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminFeedback(issuesOnly)
      .then((data: FeedbackEntry[]) => setEntries(data))
      .catch((e: Error) => setError(e.message));
  }, [issuesOnly]);

  if (error) return <div className="text-red-400 font-mono text-xs">Error: {error}</div>;

  const fmvRange = (e: FeedbackEntry) => formatFmvRange(e.fmv_low, e.fmv_high);

  return (
    <>
      <div className="flex gap-2 mb-4">
        {["All", "Issues Only"].map((label) => {
          const active = label === "Issues Only" ? issuesOnly : !issuesOnly;
          return (
            <button
              key={label}
              onClick={() => setIssuesOnly(label === "Issues Only")}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                active ? "bg-primary/15 text-primary border border-primary/30" : "bg-white/[0.04] text-on-surface/40 border border-white/[0.06]"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <DataTable
        title="Feedback Log"
        badge={`${entries.length} ENTRIES`}
        headers={["TIME", "EQUIPMENT", "FMV GIVEN", "RATING", "COMMENT"]}
      >
        {entries.map((e, i) => {
          const isDown = e.rating === "down";
          return (
            <tr
              key={i}
              onClick={() => setExpanded(expanded === i ? null : i)}
              className={`cursor-pointer hover:bg-white/[0.04] transition-colors ${isDown ? "border-l-2 border-l-primary" : ""}`}
            >
              <td className="px-6 py-3 text-on-surface/50">{e.timestamp ? timeAgo(e.timestamp) : "---"}</td>
              <td className="px-6 py-3 text-on-surface font-medium">
                {(e.user_message || "").slice(0, 50)}
                {e.user_message && e.user_message.length > 50 ? "..." : ""}
              </td>
              <td className="px-6 py-3 text-on-surface/70">{fmvRange(e)}</td>
              <td className="px-6 py-3">{isDown ? "👎" : "👍"}</td>
              <td className="px-6 py-3 text-on-surface/40 italic">{e.comment || "---"}</td>
            </tr>
          );
        })}
      </DataTable>
    </>
  );
}
