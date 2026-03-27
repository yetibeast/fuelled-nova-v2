"use client";

import { useEffect, useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchRecentReports, generateReportFromData } from "@/lib/api";

interface ReportEntry {
  timestamp: string;
  type: string;
  title: string;
  items: number;
  fmv_range: string;
  status: string;
}

const TEMPLATES: { id: string; icon: string; name: string; description: string; preview: string; disabled?: boolean }[] = [
  {
    id: "single",
    icon: "article",
    name: "Single Equipment Valuation",
    description: "Standard .docx report for one item with full methodology breakdown, comparables, and risk factors.",
    preview: "FMV analysis, depreciation curves, comparable listings, risk disclosure",
  },
  {
    id: "portfolio",
    icon: "folder_open",
    name: "Portfolio Pricing",
    description: "Multi-item report with executive summary, line-item valuations, and category rollups.",
    preview: "Executive summary, category breakdown, individual valuations, total portfolio range",
  },
  {
    id: "market",
    icon: "insights",
    name: "Market Report",
    description: "Category-level market analysis with pricing trends and competitive positioning.",
    preview: "Coming soon",
    disabled: true,
  },
];

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportEntry[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("single");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentReports()
      .then(setReports)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleDownload(report: ReportEntry) {
    try {
      const blob = await generateReportFromData({
        type: report.type,
        data: {},
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Fuelled_${report.type === "portfolio" ? "Portfolio" : "Valuation"}_Report.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Reports</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">Valuation deliverables and report generation</p>
      </div>

      {/* Section 1: Generate Report */}
      <div className="mb-8">
        <h2 className="font-headline font-bold text-sm tracking-tight mb-4">Generate Report</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {TEMPLATES.map((t) => {
            const active = selectedTemplate === t.id && !t.disabled;
            return (
              <button
                key={t.id}
                onClick={() => !t.disabled && setSelectedTemplate(t.id)}
                disabled={t.disabled}
                className={`glass-card rounded-xl p-5 text-left transition-all ${
                  t.disabled
                    ? "opacity-50 cursor-not-allowed"
                    : active
                      ? "ring-2 ring-primary/50 bg-primary/[0.04]"
                      : "hover:bg-white/[0.04] cursor-pointer"
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${active ? "bg-primary/20" : "bg-white/[0.06]"}`}>
                    <MaterialIcon icon={t.icon} className={`text-xl ${active ? "text-primary" : "text-on-surface/50"}`} />
                  </div>
                  <div>
                    <div className="font-headline font-bold text-sm">{t.name}</div>
                    {t.disabled && (
                      <span className="text-[9px] font-mono text-on-surface/30 uppercase tracking-wider">Coming soon</span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-on-surface/60 leading-relaxed mb-2">{t.description}</p>
                <div className="text-[10px] font-mono text-on-surface/30">{t.preview}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Section 2: Recent Reports */}
      <div className="mb-8">
        <div className="glass-card rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center">
            <div>
              <h3 className="font-headline font-bold text-sm tracking-tight">Recent Reports</h3>
              <p className="text-[10px] font-mono text-on-surface/30 mt-1">Previously generated valuation deliverables</p>
            </div>
            <span className="text-[10px] font-mono text-secondary">{reports.length} REPORTS</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-on-surface/30 border-b border-white/[0.05]">
                <tr>
                  <th className="px-6 py-3 font-medium">DATE</th>
                  <th className="px-6 py-3 font-medium">TYPE</th>
                  <th className="px-6 py-3 font-medium">TITLE</th>
                  <th className="px-6 py-3 font-medium text-right">ITEMS</th>
                  <th className="px-6 py-3 font-medium text-right">FMV RANGE</th>
                  <th className="px-6 py-3 font-medium">STATUS</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-on-surface/30">
                      Loading...
                    </td>
                  </tr>
                ) : reports.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-on-surface/30">
                      No reports generated yet. Use the Pricing Agent to create valuations, then export reports.
                    </td>
                  </tr>
                ) : (
                  reports.map((r, i) => (
                    <tr key={i} className="hover:bg-white/[0.04] transition-colors">
                      <td className="px-6 py-3 text-on-surface/50">{r.timestamp?.slice(0, 10)}</td>
                      <td className="px-6 py-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/[0.06]">
                          {r.type === "portfolio" ? "Portfolio" : "Single"}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-on-surface/80">{r.title}</td>
                      <td className="px-6 py-3 text-right text-on-surface/50">{r.items}</td>
                      <td className="px-6 py-3 text-right text-on-surface/70">{r.fmv_range}</td>
                      <td className="px-6 py-3">
                        <span className="text-emerald-400 text-[10px] font-mono">{r.status}</span>
                      </td>
                      <td className="px-6 py-3">
                        <button
                          onClick={() => handleDownload(r)}
                          className="flex items-center gap-1 text-primary hover:text-primary/80 transition-colors"
                        >
                          <MaterialIcon icon="download" className="text-base" />
                          <span className="text-[10px] font-mono">.docx</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Section 3: Scheduled Reports */}
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-white/[0.06] flex items-center justify-center">
            <MaterialIcon icon="schedule" className="text-xl text-on-surface/40" />
          </div>
          <div>
            <h3 className="font-headline font-bold text-sm tracking-tight">Scheduled Reports</h3>
            <p className="text-[10px] font-mono text-on-surface/30 mt-0.5">Coming soon</p>
          </div>
        </div>
        <p className="text-xs text-on-surface/50 leading-relaxed mb-4">
          Automated weekly/monthly reports for recurring client needs. Configure templates, recipients, and delivery schedules.
        </p>
        <button
          disabled
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[0.04] text-on-surface/30 text-xs font-mono cursor-not-allowed"
          title="Coming soon"
        >
          <MaterialIcon icon="add" className="text-base" />
          Set up a schedule
        </button>
      </div>
    </>
  );
}
