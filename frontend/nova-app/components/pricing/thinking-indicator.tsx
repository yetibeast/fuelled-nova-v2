"use client";

import { useState, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";

const MESSAGES = [
  "Searching 31,000 listings...",
  "Analyzing market comparables...",
  "Calculating fair market value...",
  "Checking risk factors...",
  "Building valuation summary...",
];

export function ThinkingIndicator() {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIndex((i) => (i + 1) % MESSAGES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

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
          <span className="text-secondary animate-pulse font-mono text-xs">
            {MESSAGES[msgIndex]}
          </span>
        </div>
      </div>
    </div>
  );
}
