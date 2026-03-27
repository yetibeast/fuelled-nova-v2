"use client";

import { useState, Suspense } from "react";
import { UsersTab } from "@/components/admin/users-tab";
import { FeedbackTab } from "@/components/admin/feedback-tab";
import { ValuationsTab } from "@/components/admin/valuations-tab";

const TABS = ["Users", "Feedback Log", "Valuation Log"] as const;
type Tab = (typeof TABS)[number];

function AdminSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-1 border-b border-white/[0.06] pb-2">{[1,2,3].map(i => <div key={i} className="h-6 w-24 bg-white/[0.06] rounded animate-pulse" />)}</div>
      <div className="glass-card rounded-xl p-6"><div className="h-4 w-24 bg-white/[0.06] rounded animate-pulse mb-4" /><div className="space-y-3">{[1,2,3,4,5].map(i => <div key={i} className="h-10 bg-white/[0.04] rounded animate-pulse" />)}</div></div>
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("Users");

  return (
    <>
      <div className="mb-6">
        <h1 className="font-headline font-bold text-xl tracking-tight">Administration</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">Users, feedback and valuation audit</p>
      </div>

      {/* Tab bar */}
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

      <Suspense fallback={<AdminSkeleton />}>
        {tab === "Users" && <UsersTab />}
        {tab === "Feedback Log" && <FeedbackTab />}
        {tab === "Valuation Log" && <ValuationsTab />}
      </Suspense>
    </>
  );
}
