"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

const FEATURES = [
  "Supply Chain Mapping",
  "Risk Indexing",
  "OEM Tracking",
];

export default function ManufacturersPage() {
  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      {/* Ambient glow */}
      <div
        className="absolute top-1/4 left-1/3 w-[400px] h-[400px] rounded-full opacity-[0.04] pointer-events-none"
        style={{ background: "radial-gradient(circle, #EF5D28, transparent 70%)" }}
      />
      <div
        className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] rounded-full opacity-[0.03] pointer-events-none"
        style={{ background: "radial-gradient(circle, #0ABAB5, transparent 70%)" }}
      />

      <div className="glass-card rounded-xl p-10 max-w-md w-full text-center relative z-10">
        {/* Icon with lock badge */}
        <div className="relative inline-block mb-5">
          <MaterialIcon icon="factory" className="text-[48px] text-on-surface/30" />
          <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-surface-container flex items-center justify-center border border-white/[0.08]">
            <MaterialIcon icon="lock" className="text-[14px] text-on-surface/40" />
          </div>
        </div>

        <h1 className="font-headline text-xl font-bold tracking-tight mb-1">
          Manufacturer Intelligence
        </h1>
        <p className="text-secondary text-sm font-medium mb-4">Coming Soon</p>

        <p className="text-on-surface/40 text-sm leading-relaxed mb-6">
          This workspace will identify and track equipment manufacturers and packagers for
          inventory sourcing. Build manufacturer universe by equipment category, prioritize
          OEM outreach based on historical demand, and track manufacturer relationships.
        </p>

        <button className="bg-primary text-on-primary px-6 py-2.5 rounded-lg font-medium text-sm hover:brightness-110 transition-all">
          Notify me when ready
        </button>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-2 mt-6">
          {FEATURES.map((f) => (
            <span
              key={f}
              className="px-3 py-1 rounded-full text-[11px] font-mono text-on-surface/40 border border-white/[0.08] bg-white/[0.02]"
            >
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
