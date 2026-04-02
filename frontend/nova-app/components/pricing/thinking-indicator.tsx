"use client";

import { MaterialIcon } from "@/components/ui/material-icon";

export function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="glass-card p-6 rounded-xl max-w-[85%]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
            <MaterialIcon icon="precision_manufacturing" />
          </div>
          <span className="font-headline font-bold text-sm tracking-tight">
            Nova Intelligence
          </span>
          <div className="flex items-center gap-1 ml-1">
            <span className="w-2 h-2 rounded-full bg-secondary animate-[bounce_1.4s_ease-in-out_infinite]" />
            <span className="w-2 h-2 rounded-full bg-secondary animate-[bounce_1.4s_ease-in-out_0.2s_infinite]" />
            <span className="w-2 h-2 rounded-full bg-secondary animate-[bounce_1.4s_ease-in-out_0.4s_infinite]" />
          </div>
        </div>
      </div>
    </div>
  );
}
