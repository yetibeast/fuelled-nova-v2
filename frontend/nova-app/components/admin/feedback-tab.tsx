"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/data-table";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchAdminFeedback, fetchReviewQueue, promoteEvidence } from "@/lib/api";
import { timeAgo, formatFmvRange } from "@/lib/utils";

interface FeedbackEntry {
  timestamp: string;
  rating: string;
  comment: string | null;
  user_message: string;
  fmv_low: number | null;
  fmv_mid: number | null;
  fmv_high: number | null;
  evidence_id?: string;
  user_email?: string;
  user_name?: string;
  trace_id?: string;
}

interface ReviewItem {
  id: string;
  manufacturer: string;
  model: string;
  category: string;
  price_value: number | null;
  confidence: string;
  user_message: string;
  comment: string;
  user_corrected_fmv: number | null;
  created_at: string;
  user_email?: string;
  user_name?: string;
}

export function FeedbackTab() {
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminFeedback(issuesOnly)
      .then((data: FeedbackEntry[]) => setEntries(data))
      .catch((e: Error) => setError(e.message));
  }, [issuesOnly]);

  useEffect(() => {
    fetchReviewQueue()
      .then(setReviewQueue)
      .catch(() => {});
  }, []);

  async function handlePromote(id: string) {
    setPromoting(id);
    try {
      await promoteEvidence(id);
      setReviewQueue((prev) => prev.filter((r) => r.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Promote failed");
    } finally {
      setPromoting(null);
    }
  }

  function displayUser(name?: string, email?: string): string {
    if (name) return name;
    if (email) return email;
    return "Anonymous";
  }

  if (error) return <div className="text-red-400 font-mono text-xs">Error: {error}</div>;

  const fmvRange = (e: FeedbackEntry) => formatFmvRange(e.fmv_low, e.fmv_high);

  return (
    <>
      {/* Review Queue */}
      {reviewQueue.length > 0 && (
        <div className="mb-6">
          <DataTable
            title="Review Queue"
            badge={`${reviewQueue.length} NEEDS REVIEW`}
            headers={["TIME", "USER", "EQUIPMENT", "ORIGINAL FMV", "USER CORRECTION", "COMMENT", ""]}
            headerAligns={["left", "left", "left", "right", "right", "left", "left"]}
          >
            {reviewQueue.map((r) => (
              <tr key={r.id} className="hover:bg-white/[0.04] transition-colors border-l-2 border-l-primary">
                <td className="px-6 py-3 text-on-surface/50">{r.created_at ? timeAgo(r.created_at) : "---"}</td>
                <td className="px-6 py-3 text-on-surface/60 text-xs">{displayUser(r.user_name, r.user_email)}</td>
                <td className="px-6 py-3 text-on-surface font-medium">
                  {r.manufacturer} {r.model}
                  <div className="text-[10px] text-on-surface/40">{r.category}</div>
                </td>
                <td className="px-6 py-3 text-right text-on-surface/70">
                  {r.price_value ? `$${r.price_value.toLocaleString()}` : "---"}
                </td>
                <td className="px-6 py-3 text-right">
                  {r.user_corrected_fmv ? (
                    <span className="text-secondary font-bold">${r.user_corrected_fmv.toLocaleString()}</span>
                  ) : (
                    <span className="text-on-surface/30">---</span>
                  )}
                </td>
                <td className="px-6 py-3 text-on-surface/40 italic">{r.comment || "---"}</td>
                <td className="px-6 py-3">
                  <button
                    onClick={() => handlePromote(r.id)}
                    disabled={promoting === r.id}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-secondary/10 text-secondary text-[10px] font-mono hover:bg-secondary/20 disabled:opacity-50 transition-colors"
                  >
                    <MaterialIcon icon="arrow_upward" className="text-sm" />
                    Promote to Gold
                  </button>
                </td>
              </tr>
            ))}
          </DataTable>
        </div>
      )}

      {/* Standard Feedback */}
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
        headers={["TIME", "USER", "EQUIPMENT", "FMV GIVEN", "RATING", "COMMENT", ""]}
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
              <td className="px-6 py-3 text-on-surface/60 text-xs">{displayUser(e.user_name, e.user_email)}</td>
              <td className="px-6 py-3 text-on-surface font-medium">
                {(e.user_message || "").slice(0, 50)}
                {e.user_message && e.user_message.length > 50 ? "..." : ""}
              </td>
              <td className="px-6 py-3 text-on-surface/70">{fmvRange(e)}</td>
              <td className="px-6 py-3">{isDown ? "\uD83D\uDC4E" : "\uD83D\uDC4D"}</td>
              <td className="px-6 py-3 text-on-surface/40 italic">{e.comment || "---"}</td>
              <td className="px-6 py-3">
                {e.trace_id && (
                  <a
                    href={`https://cloud.langfuse.com/trace/${e.trace_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(ev) => ev.stopPropagation()}
                    className="text-[10px] font-mono text-primary/60 hover:text-primary transition-colors underline underline-offset-2"
                  >
                    View trace
                  </a>
                )}
              </td>
            </tr>
          );
        })}
      </DataTable>
    </>
  );
}
