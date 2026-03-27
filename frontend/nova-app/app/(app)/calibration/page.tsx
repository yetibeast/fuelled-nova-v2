"use client";

import { useEffect, useState, useRef } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/ui/data-table";
import { ConfidencePill } from "@/components/ui/confidence-pill";
import {
  fetchGoldenFixtures,
  fetchCalibrationResults,
  runGoldenCalibration,
  runCalibrationUpload,
} from "@/lib/api";
import { MaterialIcon } from "@/components/ui/material-icon";

interface Fixture {
  id: string;
  description: string;
  expected_fmv_low: number;
  expected_fmv_high: number;
  category: string;
}

interface CalibrationResult {
  id: string;
  description: string;
  category: string;
  expected_low: number;
  expected_high: number;
  actual_fmv: number | null;
  confidence: string;
  status: string;
  error?: string;
  tools_used: string[];
}

interface CalibrationRun {
  timestamp: string;
  total: number;
  passed: number;
  failed: number;
  errors: number;
  accuracy_pct: number;
  results: CalibrationResult[];
}

function fmt(n: number) {
  return "$" + n.toLocaleString();
}

function statusColor(s: string) {
  if (s === "PASS") return "text-green-400";
  if (s === "FAIL") return "text-red-400";
  if (s === "NO_FMV") return "text-yellow-400";
  return "text-red-400";
}

function statusBg(s: string) {
  if (s === "PASS") return "bg-green-400/10";
  if (s === "FAIL") return "bg-red-400/10";
  if (s === "NO_FMV") return "bg-yellow-400/10";
  return "bg-red-400/10";
}

export default function CalibrationPage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [lastRun, setLastRun] = useState<CalibrationRun | null>(null);
  const [running, setRunning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([fetchGoldenFixtures(), fetchCalibrationResults()])
      .then(([f, r]) => {
        setFixtures(f);
        if (r && r.results && r.results.length > 0) setLastRun(r);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  async function handleRunGolden() {
    setRunning(true);
    setError(null);
    try {
      const results = await runGoldenCalibration();
      setLastRun(results);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const results = await runCalibrationUpload(file);
      setLastRun(results);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (error && loading) {
    return (
      <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-6 w-48 bg-white/[0.06] rounded animate-pulse" />
          <div className="h-3 w-72 bg-white/[0.04] rounded animate-pulse mt-2" />
        </div>
        <div className="glass-card rounded-xl p-6">
          <div className="h-4 w-36 bg-white/[0.06] rounded animate-pulse mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-8 bg-white/[0.04] rounded animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">
          Calibration
        </h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          Run golden fixtures or upload test cases to validate pricing accuracy
        </p>
      </div>

      {error && (
        <div className="glass-card rounded-xl p-4 mb-6 border border-red-500/20 bg-red-500/5">
          <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
            <MaterialIcon icon="error" className="text-base" />
            {error}
          </div>
        </div>
      )}

      {/* Summary metrics */}
      {lastRun && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <MetricCard label="Total" value={String(lastRun.total)} />
          <MetricCard
            label="Passed"
            value={String(lastRun.passed)}
            valueColor="text-green-400"
          />
          <MetricCard
            label="Failed"
            value={String(lastRun.failed)}
            valueColor="text-red-400"
          />
          <MetricCard
            label="Errors"
            value={String(lastRun.errors)}
            valueColor={
              lastRun.errors > 0 ? "text-yellow-400" : "text-on-surface/50"
            }
          />
          <MetricCard
            label="Accuracy"
            value={`${lastRun.accuracy_pct}%`}
            valueColor={
              lastRun.accuracy_pct >= 80 ? "text-secondary" : "text-red-400"
            }
          />
        </div>
      )}

      {/* Golden Fixtures */}
      <div className="glass-card rounded-xl overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center">
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight">
              Golden Fixtures
            </h3>
            <p className="text-[10px] font-mono text-on-surface/30 mt-1">
              {fixtures.length} known-good test cases with expected FMV ranges
            </p>
          </div>
          <button
            onClick={handleRunGolden}
            disabled={running}
            className="flex items-center gap-2 bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 disabled:opacity-50 rounded-lg py-1.5 px-4 transition-colors"
          >
            <MaterialIcon
              icon={running ? "hourglass_empty" : "play_arrow"}
              className={`text-lg ${running ? "animate-spin" : ""}`}
            />
            <span className="font-mono text-[11px] uppercase tracking-wider font-medium">
              {running ? "Running..." : "Run Golden Calibration"}
            </span>
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="text-on-surface/30 border-b border-white/[0.05]">
              <tr>
                <th className="px-6 py-3 font-medium">ID</th>
                <th className="px-6 py-3 font-medium">DESCRIPTION</th>
                <th className="px-6 py-3 font-medium">CATEGORY</th>
                <th className="px-6 py-3 font-medium text-right">
                  EXPECTED RANGE
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {fixtures.map((f) => (
                <tr
                  key={f.id}
                  className="hover:bg-white/[0.04] transition-colors"
                >
                  <td className="px-6 py-3 text-secondary font-medium">
                    {f.id}
                  </td>
                  <td className="px-6 py-3 text-on-surface/80 max-w-[400px] truncate">
                    {f.description}
                  </td>
                  <td className="px-6 py-3 text-on-surface/50">
                    {f.category}
                  </td>
                  <td className="px-6 py-3 text-right text-on-surface/70">
                    {fmt(f.expected_fmv_low)} &ndash; {fmt(f.expected_fmv_high)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload CSV */}
      <div className="glass-card rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight">
              Custom Calibration
            </h3>
            <p className="text-[10px] font-mono text-on-surface/30 mt-1">
              Upload a CSV with columns: description, expected_fmv_low,
              expected_fmv_high, category
            </p>
          </div>
          <label
            className={`flex items-center gap-2 bg-white/8 border border-secondary/25 text-secondary hover:bg-white/12 rounded-lg py-1.5 px-4 transition-colors cursor-pointer ${
              uploading ? "opacity-50 pointer-events-none" : ""
            }`}
          >
            <MaterialIcon
              icon={uploading ? "hourglass_empty" : "upload_file"}
              className={`text-lg ${uploading ? "animate-spin" : ""}`}
            />
            <span className="font-mono text-[11px] uppercase tracking-wider font-medium">
              {uploading ? "Uploading..." : "Upload CSV"}
            </span>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>
      </div>

      {/* Results */}
      {lastRun && lastRun.results.length > 0 && (
        <DataTable
          title="Calibration Results"
          subtitle={`Run: ${lastRun.timestamp.slice(0, 19).replace("T", " ")} UTC`}
          badge={`${lastRun.accuracy_pct}% ACCURACY`}
          headers={[
            "ID",
            "DESCRIPTION",
            "STATUS",
            "EXPECTED",
            "ACTUAL FMV",
            "CONFIDENCE",
          ]}
          headerAligns={["left", "left", "left", "right", "right", "left"]}
        >
          {lastRun.results.map((r) => (
            <tr
              key={r.id}
              className="hover:bg-white/[0.04] transition-colors"
            >
              <td className="px-6 py-3 text-secondary font-medium">{r.id}</td>
              <td className="px-6 py-3 text-on-surface/80 max-w-[300px] truncate">
                {r.description}
              </td>
              <td className="px-6 py-3">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${statusColor(r.status)} ${statusBg(r.status)}`}
                >
                  {r.status}
                </span>
              </td>
              <td className="px-6 py-3 text-right text-on-surface/50">
                {fmt(r.expected_low)} &ndash; {fmt(r.expected_high)}
              </td>
              <td className="px-6 py-3 text-right text-on-surface/70">
                {r.actual_fmv !== null ? fmt(r.actual_fmv) : "---"}
              </td>
              <td className="px-6 py-3">
                <ConfidencePill level={r.confidence} />
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </>
  );
}
