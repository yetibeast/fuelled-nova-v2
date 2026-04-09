"use client";

import { useState } from "react";
import { RcnTab } from "@/components/gold/rcn-tab";
import { MarketTab } from "@/components/gold/market-tab";
import { DepreciationTab } from "@/components/gold/depreciation-tab";
import { GapsTab } from "@/components/gold/gaps-tab";

const TABS = ["RCN References", "Market Values", "Depreciation", "Coverage Gaps"] as const;
type Tab = (typeof TABS)[number];

export default function GoldTablesPage() {
  const [tab, setTab] = useState<Tab>("RCN References");

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Gold Table Management</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          Curated reference data powering the pricing engine
        </p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-white/[0.06]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-xs font-mono transition-colors ${
              tab === t
                ? "text-primary border-b-2 border-primary"
                : "text-on-surface/40 hover:text-on-surface/70"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "RCN References" && <RcnTab />}
      {tab === "Market Values" && <MarketTab />}
      {tab === "Depreciation" && <DepreciationTab />}
      {tab === "Coverage Gaps" && <GapsTab />}
    </>
  );
}
