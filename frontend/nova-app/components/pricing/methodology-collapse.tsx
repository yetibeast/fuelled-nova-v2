"use client";

import { useState } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";

interface MethodologyCollapseProps {
  text: string;
}

export function MethodologyCollapse({ text }: MethodologyCollapseProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2">
          <MaterialIcon icon="calculate" className="text-secondary text-lg" />
          <span className="font-headline font-bold text-sm tracking-tight text-on-surface">
            How Nova priced this
          </span>
        </div>
        <MaterialIcon
          icon={open ? "expand_less" : "expand_more"}
          className="text-on-surface/40"
        />
      </button>
      {open && (
        <div className="px-6 pb-5 pt-0 border-t border-white/5">
          <p className="text-sm text-on-surface/70 leading-relaxed whitespace-pre-line mt-4">
            {text}
          </p>
        </div>
      )}
    </div>
  );
}
