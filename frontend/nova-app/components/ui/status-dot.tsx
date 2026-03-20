"use client";

import { statusDotClass } from "@/lib/utils";

interface StatusDotProps {
  date: string | null;
}

export function StatusDot({ date }: StatusDotProps) {
  return <span className={`status-dot ${statusDotClass(date)}`} />;
}
