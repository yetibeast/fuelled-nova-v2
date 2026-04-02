"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { uploadBatchSpreadsheet, exportBatchSpreadsheet, exportBatchReport, startBatchJob, pollBatchStatus } from "@/lib/api";

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
        if (status.current_item) {
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

  async function downloadXlsx() {
    if (!result) return;
    const blob = await exportBatchSpreadsheet(result.results);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Fuelled_Batch_Valuations.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function downloadReport() {
    if (!result) return;
    const blob = await exportBatchReport(result.results, result.summary);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Fuelled_Portfolio_Report.docx";
    a.click();
    URL.revokeObjectURL(url);
  }

  function fmt(n: number) {
    return `$${n.toLocaleString()}`;
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging ? "border-primary bg-primary/5" : "border-white/10 hover:border-white/20"
        }`}
      >
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
        <MaterialIcon icon="upload_file" className="text-3xl text-on-surface/30 mb-2" />
        <p className="text-sm text-on-surface/60">{file ? file.name : "Drop .csv or .xlsx here, or click to browse"}</p>
      </div>

      {/* Upload button */}
      {file && !result && (
        <button onClick={upload} disabled={loading} className="w-full py-2.5 rounded-lg bg-primary text-white text-sm font-medium disabled:opacity-60 transition-opacity">
          {loading ? progress : "Upload & Price All Items"}
        </button>
      )}

      {error && <div className="text-red-400 text-xs font-mono">{error}</div>}

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
            <div className="text-[10px] font-mono text-red-400">{result.summary.failed} item(s) failed</div>
          )}
          <div className="flex gap-2 pt-2">
            <button onClick={downloadXlsx} className="flex-1 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-medium text-on-surface/80 flex items-center justify-center gap-1.5 transition-colors">
              <MaterialIcon icon="table_chart" className="text-sm" /> Export XLSX
            </button>
            <button onClick={downloadReport} className="flex-1 py-2 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-xs font-medium text-on-surface/80 flex items-center justify-center gap-1.5 transition-colors">
              <MaterialIcon icon="description" className="text-sm" /> Portfolio Report
            </button>
          </div>
          <button onClick={() => { setFile(null); setResult(null); }} className="w-full text-xs text-on-surface/40 hover:text-on-surface/60 transition-colors pt-1">
            Upload another file
          </button>
        </div>
      )}
    </div>
  );
}
