"use client";

import { useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { ValuationCard } from "@/components/pricing/valuation-card";
import { ComparablesTable } from "@/components/pricing/comparables-table";
import { RiskCard } from "@/components/pricing/risk-card";
import { MethodologyCollapse } from "@/components/pricing/methodology-collapse";
import { FeedbackButtons } from "@/components/pricing/feedback-buttons";
import { ExportButton } from "@/components/pricing/export-button";
import { ResultsTable } from "@/components/pricing/results-table";
import type { ResponseData } from "@/components/pricing/conversation-sidebar";

interface BatchResult {
  title: string;
  structured: {
    valuation?: { fmv_low?: number; fmv_high?: number; confidence?: string; currency?: string; rcn?: number; factors?: { label: string; value: number | string }[] };
    comparables?: Array<{ title?: string; year?: string | number; location?: string; price?: number; currency?: string; url?: string }>;
    risks?: string[];
    methodology?: string;
    response?: string;
  };
  confidence?: string;
}

interface IntelligencePanelProps {
  lastResponse: ResponseData | null;
  conversationId: string;
  messageIndex: number;
  userMessage: string;
  batchResults?: BatchResult[];
  batchSummary?: { total_fmv_low?: number; total_fmv_high?: number };
  batchLoading?: boolean;
  batchProgress?: { completed: number; total: number; current_item?: string };
}

export function IntelligencePanel({
  lastResponse,
  conversationId,
  messageIndex,
  userMessage,
  batchResults,
  batchSummary,
  batchLoading,
  batchProgress,
}: IntelligencePanelProps) {
  const [selectedItem, setSelectedItem] = useState<number | null>(null);

  // Batch mode: show results table or drill-down
  if (batchResults && batchResults.length > 0) {
    // Drill-down into a specific item
    if (selectedItem !== null) {
      const item = batchResults[selectedItem];
      if (!item) {
        setSelectedItem(null);
        return null;
      }

      const val = item.structured?.valuation as
        | { fmv_low: number; fmv_high: number; confidence: string; currency?: string; rcn?: number; factors?: { label: string; value: number | string }[] }
        | undefined;
      const comps = (item.structured?.comparables || []) as {
        title?: string; year?: string | number; location?: string; price?: number; currency?: string; url?: string;
      }[];
      const risks = (item.structured?.risks || []) as string[];
      const methodology = (item.structured?.methodology || item.structured?.response || "") as string;

      return (
        <div className="h-full overflow-y-auto p-6 space-y-6">
          <button
            onClick={() => setSelectedItem(null)}
            className="flex items-center gap-1.5 text-xs text-secondary hover:text-primary transition-colors font-mono"
          >
            <MaterialIcon icon="arrow_back" className="text-sm" />
            Back to results
          </button>

          <div className="text-on-surface/60 text-xs font-mono uppercase tracking-widest">
            Item {selectedItem + 1} of {batchResults.length}
          </div>

          {val && val.fmv_low != null && <ValuationCard data={val} />}
          {comps.length > 0 && <ComparablesTable comparables={comps} currency={val?.currency} />}
          {risks.length > 0 && <RiskCard risks={risks} />}
          {methodology && <MethodologyCollapse text={methodology} />}
        </div>
      );
    }

    // Results table overview
    return (
      <div className="h-full overflow-y-auto p-6 space-y-6">
        <ResultsTable
          results={batchResults}
          summary={batchSummary}
          isLoading={batchLoading}
          progress={batchProgress}
          onSelectItem={setSelectedItem}
        />
      </div>
    );
  }

  // Single-item mode (unchanged)
  if (!lastResponse || !lastResponse.structured) {
    return <EmptyState />;
  }

  const s = lastResponse.structured as Record<string, unknown>;
  const valuation = s.valuation as
    | { fmv_low: number; fmv_high: number; confidence: string; currency?: string; rcn?: number; factors?: { label: string; value: number | string }[] }
    | undefined;
  const comparables = (s.comparables || []) as {
    title?: string;
    year?: string | number;
    location?: string;
    price?: number;
    currency?: string;
    url?: string;
  }[];
  const valuationCurrency = valuation?.currency;
  const risks = (s.risks || []) as string[];
  const methodology = (s.methodology || lastResponse.response || "") as string;

  const hasContent =
    (valuation && valuation.fmv_low != null) ||
    comparables.length > 0 ||
    risks.length > 0;

  if (!hasContent) return <EmptyState />;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {valuation && valuation.fmv_low != null && (
        <ValuationCard data={valuation} />
      )}

      {comparables.length > 0 && (
        <ComparablesTable comparables={comparables} currency={valuationCurrency} />
      )}

      {risks.length > 0 && <RiskCard risks={risks} />}

      {methodology && <MethodologyCollapse text={methodology} />}

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <FeedbackButtons
          conversationId={conversationId}
          messageIndex={messageIndex}
          userMessage={userMessage}
          structuredData={s}
          responseText={lastResponse.response || ""}
          traceId={lastResponse.trace_id}
        />
        <ExportButton
          structuredData={s}
          responseText={lastResponse.response || ""}
          userMessage={userMessage}
        />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="text-center space-y-4 max-w-[280px]">
        <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto">
          <MaterialIcon
            icon="insights"
            className="text-3xl text-on-surface/20"
          />
        </div>
        <p className="text-on-surface/40 text-sm leading-relaxed">
          Ask about any equipment to see the intelligence panel populate.
        </p>
        <div className="text-left text-on-surface/30 text-xs space-y-1.5 pt-2">
          <div className="flex items-center gap-2">
            <span className="text-secondary shrink-0">&bull;</span>
            Type a question
          </div>
          <div className="flex items-center gap-2">
            <span className="text-secondary shrink-0">&bull;</span>
            Upload a P&amp;ID
          </div>
          <div className="flex items-center gap-2">
            <span className="text-secondary shrink-0">&bull;</span>
            Attach a client email
          </div>
        </div>
      </div>
    </div>
  );
}
