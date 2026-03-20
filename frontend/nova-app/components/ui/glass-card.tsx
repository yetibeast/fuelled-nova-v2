"use client";

import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: "default" | "highlighted" | "recessed";
}

export function GlassCard({ children, className = "", variant = "default" }: GlassCardProps) {
  const base =
    variant === "highlighted"
      ? "glass-card-highlighted"
      : variant === "recessed"
        ? "recessed-input"
        : "glass-card";

  return <div className={`${base} rounded-xl ${className}`}>{children}</div>;
}
