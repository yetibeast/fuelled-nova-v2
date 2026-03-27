"use client";

import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/pricing/chat-panel";
import { IntelligencePanel } from "@/components/pricing/intelligence-panel";
import { BatchUpload } from "@/components/pricing/batch-upload";
import type { ResponseData } from "@/components/pricing/conversation-sidebar";

interface ResponseMeta {
  conversationId: string;
  messageIndex: number;
  userMessage: string;
}

export default function PricingPage() {
  const [tab, setTab] = useState<"chat" | "batch">("chat");
  const [lastResponse, setLastResponse] = useState<ResponseData | null>(null);
  const [meta, setMeta] = useState<ResponseMeta>({
    conversationId: "",
    messageIndex: 0,
    userMessage: "",
  });

  const handleResponse = useCallback(
    (resp: ResponseData | null, m: ResponseMeta) => {
      setLastResponse(resp);
      setMeta(m);
    },
    [],
  );

  return (
    <div className="flex h-screen -m-7 max-md:-m-4 gap-0 flex-col">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-4 pt-3 pb-0 shrink-0 border-b border-white/[0.06]">
        {(["chat", "batch"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 ${
              tab === t
                ? "border-primary text-on-surface"
                : "border-transparent text-on-surface/40 hover:text-on-surface/60"
            }`}
          >
            {t === "chat" ? "Pricing Agent" : "Batch Upload"}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === "chat" ? (
        <div className="flex flex-1 min-h-0 gap-0">
          <div className="w-[55%] min-w-0 border-r border-white/[0.06] flex flex-col">
            <ChatPanel onResponse={handleResponse} />
          </div>
          <div className="w-[45%] min-w-0 bg-surface-container-low/50">
            <IntelligencePanel
              lastResponse={lastResponse}
              conversationId={meta.conversationId}
              messageIndex={meta.messageIndex}
              userMessage={meta.userMessage}
            />
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
          <div className="mb-4">
            <h2 className="font-headline font-bold text-lg">Batch Upload</h2>
            <p className="text-on-surface/40 text-xs font-mono mt-1">
              Upload a CSV or XLSX to price multiple items at once
            </p>
          </div>
          <BatchUpload />
        </div>
      )}
    </div>
  );
}
