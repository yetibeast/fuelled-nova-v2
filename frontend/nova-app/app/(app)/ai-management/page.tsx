"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/ui/data-table";
import { ConfidencePill } from "@/components/ui/confidence-pill";
import { fetchAIPrompt, fetchAIUsage, fetchAITools, getStoredUser } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";

interface PromptInfo {
  prompt_text: string;
  prompt_length: number;
  reference_files: { name: string; size_bytes: number }[];
  model: string;
}

interface UsageInfo {
  total_queries: number;
  queries_today: number;
  queries_this_week: number;
  queries_this_month: number;
  avg_tools_per_query: number;
  confidence_distribution: Record<string, number>;
  estimated_cost: number;
}

interface ToolInfo {
  tool_name: string;
  call_count: number;
  avg_per_query: number;
}

export default function AIManagementPage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState<PromptInfo | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [promptOpen, setPromptOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const user = getStoredUser();
    if (user?.role !== "admin") { router.replace("/"); return; }
    Promise.all([fetchAIPrompt(), fetchAIUsage(), fetchAITools()])
      .then(([p, u, t]) => { setPrompt(p); setUsage(u); setTools(t); })
      .catch((e: Error) => setError(e.message));
  }, [router]);

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">AI Management</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">System configuration, usage and tool statistics</p>
      </div>

      {/* Section 1: System Configuration */}
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-4">System Configuration</h3>
        <div className="space-y-3 font-mono text-xs">
          {[
            ["Model", prompt?.model || "---"],
            ["Prompt Length", prompt ? `${prompt.prompt_length.toLocaleString()} chars` : "---"],
            ["Reference Files", prompt ? `${prompt.reference_files.length} files` : "---"],
          ].map(([label, val], i) => (
            <div key={i} className="flex justify-between items-center py-2 border-b border-white/[0.04] last:border-0">
              <span className="text-on-surface/60">{label}</span>
              <span className="text-on-surface/80">{val}</span>
            </div>
          ))}
          {prompt?.reference_files.map((f) => (
            <div key={f.name} className="flex justify-between items-center py-1 pl-4">
              <span className="text-on-surface/40">{f.name}</span>
              <span className="text-on-surface/30">{formatFileSize(f.size_bytes)}</span>
            </div>
          ))}
        </div>
        <button
          onClick={() => setPromptOpen(!promptOpen)}
          className="mt-4 text-[11px] font-mono text-primary hover:text-primary/80 transition-colors"
        >
          {promptOpen ? "Hide system prompt" : "View system prompt"}
        </button>
        {promptOpen && prompt && (
          <pre className="mt-3 p-4 rounded-lg bg-surface-container-lowest text-[11px] font-mono text-on-surface/60 max-h-[400px] overflow-auto whitespace-pre-wrap break-words">
            {prompt.prompt_text}
          </pre>
        )}
      </div>

      {/* Section 2: API Usage */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Queries Today" value={String(usage?.queries_today ?? "--")} />
        <MetricCard label="This Week" value={String(usage?.queries_this_week ?? "--")} />
        <MetricCard label="This Month" value={String(usage?.queries_this_month ?? "--")} />
        <MetricCard label="Est. Cost" value={usage ? `$${usage.estimated_cost.toFixed(2)}` : "--"} valueColor="text-secondary" />
      </div>

      {usage && (
        <div className="flex gap-3 mb-6">
          {(["HIGH", "MEDIUM", "LOW"] as const).map((level) => (
            <div key={level} className="flex items-center gap-2">
              <ConfidencePill level={level} />
              <span className="text-xs font-mono text-on-surface/50">
                {usage.confidence_distribution[level] || 0}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Section 3: Tool Statistics */}
      <DataTable
        title="Tool Statistics"
        badge={`${tools.length} TOOLS`}
        headers={["TOOL NAME", "TOTAL CALLS", "AVG / QUERY"]}
        headerAligns={["left", "right", "right"]}
      >
        {tools.map((t) => (
          <tr key={t.tool_name} className="hover:bg-white/[0.04] transition-colors">
            <td className="px-6 py-3 text-on-surface font-medium">{t.tool_name}</td>
            <td className="px-6 py-3 text-right text-on-surface/70">{t.call_count}</td>
            <td className="px-6 py-3 text-right text-on-surface/50">{t.avg_per_query}</td>
          </tr>
        ))}
      </DataTable>
    </>
  );
}
