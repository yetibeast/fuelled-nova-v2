"use client";

import { confidenceColor } from "@/lib/utils";

interface ConfidencePillProps {
  level: string;
}

export function ConfidencePill({ level }: ConfidencePillProps) {
  const color = confidenceColor(level);
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold"
      style={{ background: color + "1a", color }}
    >
      {level}
    </span>
  );
}
