"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

interface RiskCardProps {
  risks: string[];
}

export function RiskCard({ risks }: RiskCardProps) {
  if (!risks.length) return null;

  return (
    <div className="glass-card p-5 rounded-xl bg-primary/5 border-primary/20 border flex gap-4">
      <MaterialIcon icon="report" className="text-primary shrink-0" />
      <div className="space-y-1">
        <h4 className="font-headline font-bold text-sm text-primary tracking-tight">
          Technical Risk Advisory
        </h4>
        <p className="text-sm text-on-surface/80 leading-relaxed italic">
          {risks.map((r, i) => (
            <span key={i}>
              {r}
              {i < risks.length - 1 && <br />}
            </span>
          ))}
        </p>
      </div>
    </div>
  );
}
