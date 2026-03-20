"use client";

import { fileIcon, formatFileSize } from "@/lib/utils";

interface FilePillsProps {
  files: File[];
  onRemove: (index: number) => void;
}

export function FilePills({ files, onRemove }: FilePillsProps) {
  if (files.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-1 pb-2">
      {files.map((f, idx) => (
        <div
          key={`${f.name}-${idx}`}
          className="inline-flex items-center gap-2 bg-white/[0.06] backdrop-blur-sm border border-secondary/20 rounded-lg px-3 py-1.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] group"
        >
          <span className="text-sm shrink-0">{fileIcon(f.name)}</span>
          <div className="flex flex-col leading-tight">
            <span className="text-[11px] font-mono text-on-surface/90 truncate max-w-[140px]">
              {f.name}
            </span>
            <span className="text-[9px] font-mono text-on-surface/40">
              {formatFileSize(f.size)}
            </span>
          </div>
          <button
            onClick={() => onRemove(idx)}
            className="w-5 h-5 flex items-center justify-center rounded-full hover:bg-white/10 text-on-surface/30 hover:text-white text-sm transition-colors shrink-0"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
