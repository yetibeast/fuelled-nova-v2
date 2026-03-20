"use client";

import { useState } from "react";
import { fileIcon, formatFileSize } from "@/lib/utils";

/* ---------- Markdown helpers ---------- */

function escapeHtml(text: string) {
  const d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

function bold(html: string) {
  return html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>');
}

function renderMarkdown(text: string) {
  return text
    .split(/\n\n+/)
    .map((block) => {
      block = block.trim();
      if (!block) return "";
      if (block.startsWith("### "))
        return `<h4 class="font-headline font-bold text-sm text-on-surface mt-2">${bold(escapeHtml(block.slice(4)))}</h4>`;
      if (block.startsWith("## "))
        return `<h3 class="font-headline font-bold text-base text-white mt-3">${bold(escapeHtml(block.slice(3)))}</h3>`;
      const lines = block.split("\n");
      const listLines = lines.filter((l) => /^\s*[-*\d.]+[\s)]+/.test(l));
      if (listLines.length === lines.length && listLines.length > 0) {
        return lines
          .map(
            (l) =>
              `<div class="flex gap-2 text-sm"><span class="text-secondary shrink-0">&bull;</span><span class="text-[#F2E9E1]/80">${bold(escapeHtml(l.replace(/^\s*[-*\d.]+[\s)]+/, "")))}</span></div>`,
          )
          .join("");
      }
      return `<p class="text-[#F2E9E1] leading-relaxed">${bold(escapeHtml(block)).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

/* ---------- User message ---------- */

interface FileInfo {
  name: string;
  size?: number;
}

interface UserMessageProps {
  text: string;
  files?: FileInfo[];
}

export function UserMessage({ text, files }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="glass-card p-5 rounded-xl max-w-[85%] bg-surface-container-highest/40 border-primary/20">
        <p className="text-on-surface leading-relaxed">{text}</p>
        {files && files.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-white/5">
            {files.map((f, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 bg-white/[0.04] border border-white/10 text-on-surface/70 text-[10px] font-mono rounded-lg px-2.5 py-1"
              >
                <span style={{ fontSize: 11 }}>{fileIcon(f.name)}</span>
                {f.name}
                {f.size != null && (
                  <span className="text-on-surface/30">{formatFileSize(f.size)}</span>
                )}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Nova message ---------- */

interface NovaMessageProps {
  text: string;
}

export function NovaMessage({ text }: NovaMessageProps) {
  const [expanded, setExpanded] = useState(false);

  const needsTruncation = text.length > 200;
  const truncated = needsTruncation
    ? text.slice(0, 200).replace(/\s+\S*$/, "") + "..."
    : text;

  const displayText = !needsTruncation || expanded ? text : truncated;

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-4">
        <div
          dangerouslySetInnerHTML={{ __html: renderMarkdown(displayText) }}
        />
        {needsTruncation && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-secondary hover:text-secondary/80 text-sm font-medium mt-2 transition-colors cursor-pointer"
          >
            {expanded ? "\u25BE Collapse" : "Show full analysis \u25B8"}
          </button>
        )}
      </div>
    </div>
  );
}
