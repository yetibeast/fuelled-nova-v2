"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/api";
import { UsersTab } from "@/components/admin/users-tab";
import { FeedbackTab } from "@/components/admin/feedback-tab";
import { ValuationsTab } from "@/components/admin/valuations-tab";

const TABS = ["Users", "Feedback Log", "Valuation Log"] as const;
type Tab = (typeof TABS)[number];

export default function AdminPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("Users");

  useEffect(() => {
    const user = getStoredUser();
    if (user?.role !== "admin") router.replace("/");
  }, [router]);

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

      {tab === "Users" && <UsersTab />}
      {tab === "Feedback Log" && <FeedbackTab />}
      {tab === "Valuation Log" && <ValuationsTab />}
    </>
  );
}
