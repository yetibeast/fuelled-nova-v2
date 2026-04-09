"use client";

import { useEffect, useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { fetchRiskRules } from "@/lib/api";
import { DepreciationTable } from "@/components/methodology/depreciation-table";
import { RcnBenchmarks } from "@/components/methodology/rcn-benchmarks";

interface RiskRule { title: string; trigger: string; disclosure: string; cost_impact: string; valuation_impact: string }
interface RiskCategory { title: string; rules: RiskRule[] }

const PIPELINE = [
  { icon: "search", label: "Input Parsing", desc: "Extract equipment type, specs, condition" },
  { icon: "storage", label: "RCN Lookup", desc: "Base cost from reference tables, HP/weight scaling" },
  { icon: "trending_down", label: "Depreciation", desc: "Category-specific age curves, interpolation" },
  { icon: "tune", label: "Market Factors", desc: "NACE, H2S, material, drive, geography, WTI" },
  { icon: "compare_arrows", label: "Comparables", desc: "Peer median from listings DB" },
  { icon: "calculate", label: "FMV Calc", desc: "RCN_adj x Age x Cond x Mkt x Geo" },
];

export default function MethodologyPage() {
  const [risks, setRisks] = useState<RiskCategory[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => { fetchRiskRules().then(setRisks).catch(() => {}); }, []);

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Pricing Methodology</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">How Nova calculates fair market value</p>
      </div>

      {/* Pipeline */}
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Valuation Pipeline</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {PIPELINE.map((s, i) => (
            <div key={i} className="text-center">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mx-auto mb-2">
                <MaterialIcon icon={s.icon} className="text-[20px] text-primary" />
              </div>
              <div className="text-[11px] font-mono text-on-surface font-medium">{s.label}</div>
              <div className="text-[9px] font-mono text-on-surface/40 mt-1 leading-relaxed">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <DepreciationTable />
      <RcnBenchmarks />

      {/* Risk Rules */}
      <div className="glass-card rounded-xl p-6 mb-6">
        <h3 className="font-headline font-bold text-sm tracking-tight mb-4">Risk Assessment Rules</h3>
        {risks.length === 0 ? (
          <p className="text-on-surface/30 text-xs font-mono">No risk rules loaded</p>
        ) : (
          <div className="space-y-2">
            {risks.map((cat) => (
              <div key={cat.title} className="border border-white/[0.06] rounded-lg overflow-hidden">
                <button onClick={() => setExpanded(expanded === cat.title ? null : cat.title)}
                  className="w-full px-4 py-3 flex justify-between items-center hover:bg-white/[0.04] transition-colors">
                  <span className="text-xs font-mono text-on-surface font-medium">
                    {cat.title} <span className="text-on-surface/30">({cat.rules.length})</span>
                  </span>
                  <MaterialIcon icon={expanded === cat.title ? "expand_less" : "expand_more"} className="text-[18px] text-on-surface/40" />
                </button>
                {expanded === cat.title && (
                  <div className="px-4 pb-4 space-y-3">
                    {cat.rules.map((r, i) => (
                      <div key={i} className="p-3 rounded-lg bg-surface-container-lowest">
                        <div className="text-xs font-mono text-on-surface font-medium mb-2">{r.title}</div>
                        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                          {r.trigger && <div><span className="text-on-surface/40">Trigger:</span> <span className="text-on-surface/70">{r.trigger}</span></div>}
                          {r.cost_impact && <div><span className="text-on-surface/40">Cost:</span> <span className="text-primary">{r.cost_impact}</span></div>}
                          {r.valuation_impact && <div><span className="text-on-surface/40">Valuation:</span> <span className="text-red-400">{r.valuation_impact}</span></div>}
                          {r.disclosure && <div className="col-span-2"><span className="text-on-surface/40">Disclosure:</span> <span className="text-on-surface/60">{r.disclosure}</span></div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
