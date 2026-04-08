"use client";

import { useRef } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { FilePills } from "@/components/pricing/file-pills";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.csv,.eml";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  files: File[];
  onFilesSelected: (files: File[]) => void;
  onRemoveFile: (index: number) => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  files,
  onFilesSelected,
  onRemoveFile,
  disabled,
}: ChatInputProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  const placeholder =
    files.length > 0 && !value.trim()
      ? "Analyze this document"
      : "Ask about equipment or valuation data...";

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files;
    if (!picked) return;
    const arr: File[] = [];
    for (let i = 0; i < picked.length; i++) arr.push(picked[i]);
    onFilesSelected(arr);
    e.target.value = "";
  }

  return (
    <div className="bg-white/10 backdrop-blur-2xl rounded-2xl p-2.5 border border-white/20 shadow-[0_20px_50px_rgba(0,0,0,0.5)] transition-all">
      <FilePills files={files} onRemove={onRemoveFile} />
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={() => fileRef.current?.click()}
          className="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center text-secondary border border-secondary/30 hover:bg-secondary/10 rounded-xl transition-colors shrink-0"
        >
          <MaterialIcon icon="attach_file" />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="recessed-input border border-white/5 focus:border-primary/50 focus:ring-4 focus:ring-primary/10 rounded-xl text-sm sm:text-base flex-1 min-w-0 py-3 px-3 sm:px-4 text-on-surface placeholder:text-on-surface/30 transition-all font-body outline-none"
        />
        <button
          onClick={onSend}
          disabled={disabled}
          className="bg-primary text-white h-10 sm:h-12 px-3 sm:px-6 flex items-center justify-center rounded-xl shadow-[0_8px_20px_rgba(239,93,40,0.3)] hover:brightness-110 hover:translate-y-[-1px] active:translate-y-[1px] transition-all gap-2 group shrink-0"
        >
          <span className="font-headline font-bold text-xs sm:text-sm tracking-wide hidden sm:inline">
            SEND
          </span>
          <MaterialIcon
            icon="send"
            filled
            className="text-lg sm:text-xl transition-transform group-hover:translate-x-1"
          />
        </button>
      </div>
    </div>
  );
}
