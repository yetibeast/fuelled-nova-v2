"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { uploadBatchSpreadsheet, exportBatchSpreadsheet, exportBatchReport, startBatchJob, pollBatchStatus, priceReviewedItems, type BatchReviewItem } from "@/lib/api";

interface BatchResult {
  results: Record<string, unknown>[];
  errors: { title: string; error: string }[];
  summary: { total: number; completed: number; failed: number; total_fmv_low: number; total_fmv_high: number };
}

interface BatchUploadProps {
  onBatchResults?: (results: Record<string, unknown>[], summary: Record<string, unknown>) => void;
}

export function BatchUpload({ onBatchResults }: BatchUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<BatchResult | null>(null);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [reviewItems, setReviewItems] = useState<BatchReviewItem[] | null>(null);
  const [selected, setSelected] = useState<boolean[]>([]);
  const [clientName, setClientName] = useState("");
  const [buyerOffer, setBuyerOffer] = useState("");
  const [showErrors, setShowErrors] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [xlsxLoading, setXlsxLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setResult(null);
    setReviewItems(null);
    setError("");
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  function stopPolling() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setJobId(null);
  }

  function startPolling(id: string) {
    setJobId(id);
    pollingRef.current = setInterval(async () => {
      try {
        const status = await pollBatchStatus(id);
        if (status.status === "awaiting_review") {
          // Parse done — pause for human review before pricing. Keep jobId
          // (don't call stopPolling, which clears it) so we can price the kept rows.
          if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
          const items: BatchReviewItem[] = status.items ?? [];
          setReviewItems(items);
          setSelected(items.map(() => true));
          setProgress("");
          setLoading(false);
          return;
        }
        if (status.status === "parsing") {
          setProgress(status.current_item ?? "Analyzing file...");
        } else if (status.current_item) {
          setProgress(`Pricing item ${status.completed ?? 0} of ${status.total ?? "?"}... ${status.current_item}`);
        }
        if (status.status === "completed") {
          stopPolling();
          const data: BatchResult = {
            results: status.results ?? [],
            errors: status.errors ?? [],
            summary: status.summary ?? { total: 0, completed: 0, failed: 0, total_fmv_low: 0, total_fmv_high: 0 },
          };
          setResult(data);
          setProgress("");
          setLoading(false);
          if (onBatchResults) onBatchResults(data.results, data.summary);
        } else if (status.status === "failed") {
          stopPolling();
          setError(status.error ?? "Batch job failed");
          setProgress("");
          setLoading(false);
        }
      } catch {
        stopPolling();
        setError("Lost connection to batch job");
        setProgress("");
        setLoading(false);
      }
    }, 2000);
  }

  async function upload() {
    if (!file) return;
    setLoading(true);
    setError("");
    setProgress("Starting batch job...");

    // Try async polling mode first, fall back to synchronous upload
    try {
      const { job_id } = await startBatchJob(file);
      startPolling(job_id);
    } catch {
      // Fallback to synchronous upload
      setProgress("Uploading and pricing items...");
      try {
        const data = await uploadBatchSpreadsheet(file);
        setResult(data);
        setProgress("");
        if (onBatchResults) onBatchResults(data.results, data.summary);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setProgress("");
      } finally {
        setLoading(false);
      }
    }
  }

  const selectedCount = selected.filter(Boolean).length;

  async function priceSelected() {
    if (!jobId || !reviewItems) return;
    const kept = reviewItems.filter((_, i) => selected[i]);
    if (kept.length === 0) return;
    setReviewItems(null);
    setLoading(true);
    setProgress("Starting pricing...");
    try {
      await priceReviewedItems(jobId, kept);
      startPolling(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start pricing");
      setLoading(false);
      setProgress("");
    }
  }

  function cancelReview() {
    stopPolling();
    setReviewItems(null);
    setSelected([]);
    setFile(null);
    setError("");
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadXlsx() {
    if (!result) return;
    setXlsxLoading(true);
    setError("");
    try {
      const blob = await exportBatchSpreadsheet(result.results);
      triggerDownload(blob, "Fuelled_Batch_Valuations.xlsx");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setXlsxLoading(false);
    }
  }

  async function downloadReport() {
    if (!result) return;
    const offerNum = buyerOffer ? Number(buyerOffer) : null;
    setReportLoading(true);
    setError("");
    try {
      const blob = await exportBatchReport(
        result.results,
        result.summary,
        clientName.trim() || undefined,
        Number.isFinite(offerNum) ? offerNum : null,
      );
      const safeClient = clientName.trim().replace(/[^a-zA-Z0-9]+/g, "_");
      triggerDownload(blob, safeClient ? `Fuelled_Portfolio_Report_${safeClient}.docx` : "Fuelled_Portfolio_Report.docx");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setReportLoading(false);
    }
  }

  function fmt(n: number) {
    return `$${n.toLocaleString()}`;
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      {!reviewItems && !result && (
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging ? "border-primary bg-primary/5" : "border-white/10 hover:border-white/20"
        }`}
      >
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls,.eml" className="hidden" onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
        <MaterialIcon icon="upload_file" className="text-3xl text-on-surface/30 mb-2" />
        <p className="text-sm text-on-surface/60">{file ? file.name : "Drop .xlsx, .csv, or .eml here, or click to browse"}</p>
      </div>
      )}

      {/* Upload button */}
      {file && !reviewItems && !result && (
        <button onClick={upload} disabled={loading} className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-60 transition-opacity">
          {loading ? progress : "Upload & Extract Items"}
        </button>
      )}

      {error && <div className="text-red-400 text-xs font-mono">{error}</div>}

      {/* Review step — drop junk rows before pricing */}
      {reviewItems && !result && (
        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <MaterialIcon icon="fact_check" className="text-primary text-lg" />
            <span className="font-headline font-bold text-sm">Review extracted items</span>
          </div>
          <p className="text-[11px] text-on-surface/50">
            Found {reviewItems.length} item{reviewItems.length === 1 ? "" : "s"}. Uncheck anything that isn&apos;t equipment (headers, totals, blank rows), then price.
          </p>
          <div className="rounded-md border border-white/10 divide-y divide-white/5 max-h-72 overflow-y-auto">
            {reviewItems.map((it, i) => (
              <label key={i} className="flex items-start gap-2 p-2 cursor-pointer hover:bg-white/[0.03] transition-colors">
                <input
                  type="checkbox"
                  checked={selected[i] ?? false}
                  onChange={() => setSelected((s) => s.map((v, j) => (j === i ? !v : v)))}
                  className="mt-0.5 accent-primary"
                />
                <span className="min-w-0">
                  <span className="block text-xs text-on-surface/90 truncate">{it.title || "(blank)"}</span>
                  <span className="block text-[10px] font-mono text-on-surface/40">
                    {it.category || "no category"}
                    {it.specs && Object.keys(it.specs).length > 0
                      ? " · " + Object.entries(it.specs).map(([k, v]) => `${k}: ${v}`).join(", ")
                      : ""}
                  </span>
                </span>
              </label>
            ))}
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={priceSelected}
              disabled={selectedCount === 0}
              className="flex-1 py-2 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-40 transition-opacity"
            >
              Price {selectedCount} selected item{selectedCount === 1 ? "" : "s"}
            </button>
            <button onClick={cancelReview} className="px-4 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-medium text-on-surface/70 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Results summary */}
      {result && (
        <div className="glass-card rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <MaterialIcon icon="check_circle" className="text-secondary text-lg" />
            <span className="font-headline font-bold text-sm">Batch Complete</span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-lg font-bold text-on-surface">{result.summary.completed}/{result.summary.total}</div>
              <div className="text-[9px] font-mono text-on-surface/40 uppercase">Priced</div>
            </div>
            <div>
              <div className="text-lg font-bold text-secondary">{fmt(result.summary.total_fmv_low)}</div>
              <div className="text-[9px] font-mono text-on-surface/40 uppercase">FMV Low</div>
            </div>
            <div>
              <div className="text-lg font-bold text-primary">{fmt(result.summary.total_fmv_high)}</div>
              <div className="text-[9px] font-mono text-on-surface/40 uppercase">FMV High</div>
            </div>
          </div>
          {result.summary.failed > 0 && (
            <div className="space-y-1">
              <button
                onClick={() => setShowErrors((s) => !s)}
                className="text-[10px] font-mono text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
              >
                <MaterialIcon icon={showErrors ? "expand_less" : "expand_more"} className="text-xs" />
                {result.summary.failed} item(s) failed — {showErrors ? "hide" : "show"} details
              </button>
              {showErrors && result.errors.length > 0 && (
                <div className="rounded-md bg-red-500/[0.05] border border-red-500/20 p-2 space-y-1 max-h-40 overflow-y-auto">
                  {result.errors.map((e, i) => (
                    <div key={i} className="text-[10px] font-mono text-red-300/90">
                      <span className="text-red-200 font-semibold">{e.title}:</span> {e.error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {/* Report metadata inputs */}
          <div className="grid grid-cols-2 gap-2 pt-1">
            <input
              type="text"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="Client name (optional)"
              className="px-3 py-1.5 rounded-md bg-white/[0.04] border border-white/10 text-xs text-on-surface placeholder:text-on-surface/30 focus:outline-none focus:border-primary/40 transition-colors"
            />
            <input
              type="number"
              value={buyerOffer}
              onChange={(e) => setBuyerOffer(e.target.value)}
              placeholder="Buyer offer ($, optional)"
              className="px-3 py-1.5 rounded-md bg-white/[0.04] border border-white/10 text-xs text-on-surface placeholder:text-on-surface/30 focus:outline-none focus:border-primary/40 transition-colors"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button onClick={downloadXlsx} disabled={xlsxLoading || reportLoading} className="flex-1 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-medium text-on-surface/80 flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50">
              <MaterialIcon icon="table_chart" className="text-sm" /> {xlsxLoading ? "Exporting…" : "Export XLSX"}
            </button>
            <button onClick={downloadReport} disabled={reportLoading || xlsxLoading} className="flex-1 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-medium text-on-surface/80 flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50">
              <MaterialIcon icon="description" className="text-sm" /> {reportLoading ? "Generating… (~1 min)" : "Portfolio Report"}
            </button>
          </div>
          <button onClick={() => { setFile(null); setResult(null); setReviewItems(null); }} className="w-full text-xs text-on-surface/40 hover:text-on-surface/60 transition-colors pt-1">
            Upload another file
          </button>
        </div>
      )}
    </div>
  );
}
