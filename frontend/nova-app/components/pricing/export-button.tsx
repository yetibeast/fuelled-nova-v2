"use client";

import { useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { generateReport } from "@/lib/api";

interface ExportButtonProps {
  structuredData: Record<string, unknown>;
  responseText: string;
  userMessage: string;
}

export function ExportButton({
  structuredData,
  responseText,
  userMessage,
}: ExportButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handleExport() {
    if (loading) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("structured_data", JSON.stringify(structuredData));
      fd.append("response_text", responseText);
      fd.append("user_message", userMessage || "Equipment Valuation");
      const blob = await generateReport(fd);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Fuelled_Valuation_Report.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to generate report. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className={`flex items-center gap-3 bg-white/8 border border-primary/25 text-primary/80 rounded-full py-2.5 px-8 hover:bg-white/12 hover:text-primary transition-all group ${
        loading ? "opacity-50 cursor-wait" : ""
      }`}
    >
      <MaterialIcon
        icon="description"
        className="text-xl group-hover:rotate-12 transition-transform"
      />
      <span className="font-mono text-[11px] uppercase tracking-[0.15em] font-bold">
        {loading ? "Generating..." : "Export Report"}
      </span>
    </button>
  );
}
