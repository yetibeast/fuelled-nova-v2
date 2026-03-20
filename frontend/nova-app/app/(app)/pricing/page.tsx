"use client";

import { useState, useCallback } from "react";
import { ChatPanel } from "@/components/pricing/chat-panel";
import { IntelligencePanel } from "@/components/pricing/intelligence-panel";
import type { ResponseData } from "@/components/pricing/conversation-sidebar";

interface ResponseMeta {
  conversationId: string;
  messageIndex: number;
  userMessage: string;
}

export default function PricingPage() {
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
    <div className="flex h-[calc(100vh-56px)] -m-7 max-md:-m-4 gap-0">
      {/* Chat panel — 55% */}
      <div className="w-[55%] min-w-0 border-r border-white/[0.06] flex flex-col">
        <ChatPanel onResponse={handleResponse} />
      </div>

      {/* Intelligence panel — 45% */}
      <div className="w-[45%] min-w-0 bg-surface-container-low/50">
        <IntelligencePanel
          lastResponse={lastResponse}
          conversationId={meta.conversationId}
          messageIndex={meta.messageIndex}
          userMessage={meta.userMessage}
        />
      </div>
    </div>
  );
}
