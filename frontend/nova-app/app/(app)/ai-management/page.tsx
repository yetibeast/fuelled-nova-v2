"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/metric-card";
import { DataTable } from "@/components/ui/data-table";
import { ConfidencePill } from "@/components/ui/confidence-pill";
import {
  fetchAIPrompt,
  fetchAIUsage,
  fetchAITools,
  fetchDailyUsage,
  fetchCostHistory,
  fetchModelBreakdown,
} from "@/lib/api";
import { formatFileSize } from "@/lib/utils";
import {
  BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

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

interface DailyPoint {
  date: string;
  count: number;
}

interface CostHistory {
  daily: { date: string; queries: number; cost: number }[];
  monthly_total: number;
  avg_daily: number;
  projected_monthly: number;
}

interface ModelBreakdown {
  model: string;
  queries: number;
  cost: number;
  pct: number;
}

type CostRange = 7 | 14 | 30;

export default function AIManagementPage() {
  const [prompt, setPrompt] = useState<PromptInfo | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [daily, setDaily] = useState<DailyPoint[]>([]);
  const [costHistory, setCostHistory] = useState<CostHistory | null>(null);
  const [modelBreakdown, setModelBreakdown] = useState<ModelBreakdown[]>([]);
  const [costRange, setCostRange] = useState<CostRange>(30);
  const [promptOpen, setPromptOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchAIPrompt(),
      fetchAIUsage(),
      fetchAITools(),
      fetchDailyUsage(),
      fetchCostHistory(),
      fetchModelBreakdown(),
    ])
      .then(([p, u, t, d, ch, mb]) => {
        setPrompt(p);
        setUsage(u);
        setTools(t);
        setDaily(d);
        setCostHistory(ch);
        setModelBreakdown(mb);
        setLoading(false);
      })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, []);

  const filteredCost = costHistory?.daily.slice(-costRange) ?? [];

  if (error) return <div className="text-red-400 font-mono text-sm p-4">Error: {error}</div>;

  if (loading) {
    return (
      <div className="space-y-6">
        <div><div className="h-6 w-48 bg-white/[0.06] rounded animate-pulse" /><div className="h-3 w-72 bg-white/[0.04] rounded animate-pulse mt-2" /></div>
        <div className="glass-card rounded-xl p-6"><div className="h-4 w-36 bg-white/[0.06] rounded animate-pulse mb-4" /><div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-8 bg-white/[0.04] rounded animate-pulse" />)}</div></div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">{[1,2,3,4].map(i => <div key={i} className="glass-card rounded-xl p-5"><div className="h-3 w-16 bg-white/[0.06] rounded animate-pulse mb-2" /><div className="h-7 w-12 bg-white/[0.04] rounded animate-pulse" /></div>)}</div>
        <div className="glass-card rounded-xl p-6 h-52 animate-pulse bg-white/[0.03]" />
      </div>
    );
  }

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">AI Management</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">System configuration, usage, cost and tool statistics</p>
      </div>

      {/* Cost Overview */}
      {costHistory && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard label="Monthly Spend" value={`$${costHistory.monthly_total.toFixed(2)}`} valueColor="text-secondary" />
          <MetricCard label="Avg Daily" value={`${costHistory.avg_daily} queries`} />
          <MetricCard
            label="Projected Monthly"
            value={`$${costHistory.projected_monthly.toFixed(2)}`}
            valueColor={costHistory.projected_monthly > 500 ? "text-red-400" : "text-secondary"}
          />
          <MetricCard label="Total Queries" value={String(usage?.total_queries ?? "--")} />
        </div>
      )}

      {costHistory && costHistory.projected_monthly > 500 && (
        <div className="glass-card rounded-xl p-4 mb-6 border border-red-500/20 bg-red-500/5">
          <div className="flex items-center gap-2 text-red-400 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            Budget alert: Projected monthly spend exceeds $500
          </div>
        </div>
      )}

      {/* 30-Day Cost Chart */}
      {filteredCost.length > 0 && (
        <div className="glass-card rounded-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-headline font-bold text-sm tracking-tight">Cost History</h3>
            <div className="flex gap-1">
              {([7, 14, 30] as CostRange[]).map((d) => (
                <button
                  key={d}
                  onClick={() => setCostRange(d)}
                  className={`px-3 py-1 rounded-md text-[10px] font-mono transition-colors ${
                    costRange === d
                      ? "bg-primary/20 text-primary"
                      : "text-on-surface/40 hover:text-on-surface/60"
                  }`}
                >
                  {d}D
                </button>
              ))}
            </div>
          </div>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={filteredCost} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ABAB5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0ABAB5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontFamily: "monospace" }}
                  tickFormatter={(v: string) => v.slice(5)}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: "#0e1525", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}
                  formatter={(value, name) => [
                    name === "cost" ? `$${Number(value).toFixed(2)}` : value,
                    name === "cost" ? "Cost" : "Queries",
                  ]}
                />
                <Area type="monotone" dataKey="cost" stroke="#0ABAB5" fill="url(#costFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Model Breakdown */}
      {modelBreakdown.length > 0 && (
        <div className="glass-card rounded-xl p-6 mb-6">
          <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Model Breakdown</h3>
          <div className="space-y-3">
            {modelBreakdown.map((m) => (
              <div key={m.model} className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-mono text-on-surface/80 truncate">{m.model}</span>
                    <span className="text-xs font-mono text-on-surface/50">{m.queries} queries &middot; ${m.cost.toFixed(2)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-secondary"
                      style={{ width: `${m.pct}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs font-mono text-on-surface/40 w-12 text-right">{m.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Configuration */}
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

      {/* API Usage */}
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

      {/* 7-Day Usage Chart */}
      {daily.length > 0 && (
        <div className="glass-card rounded-xl p-6 mb-6">
          <h3 className="font-headline font-bold text-sm tracking-tight mb-4">7-Day Query Volume</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={daily} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontFamily: "monospace" }}
                  tickFormatter={(v: string) => v.slice(5)}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{ background: "#0e1525", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }}
                  labelStyle={{ color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}
                  itemStyle={{ color: "#0ABAB5" }}
                />
                <Bar dataKey="count" fill="#0ABAB5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Tool Statistics */}
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
