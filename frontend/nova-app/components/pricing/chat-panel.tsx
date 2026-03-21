"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { sendPriceQuery } from "@/lib/api";
import { ChatInput } from "@/components/pricing/chat-input";
import { UserMessage, NovaMessage } from "@/components/pricing/chat-message";
import { ThinkingIndicator } from "@/components/pricing/thinking-indicator";
import {
  ConversationSidebar,
  loadConversations,
  saveConversations,
} from "@/components/pricing/conversation-sidebar";
import type {
  Conversation,
  ResponseData,
} from "@/components/pricing/conversation-sidebar";

/* ---------- Types ---------- */

interface ChatEntry {
  role: "user" | "nova";
  text: string;
  files?: { name: string; size?: number }[];
  data?: ResponseData | null;
  isError?: boolean;
  errorDetail?: string;
}

interface ChatPanelProps {
  onResponse: (resp: ResponseData | null, meta: { conversationId: string; messageIndex: number; userMessage: string }) => void;
}

/* ---------- Component ---------- */

export function ChatPanel({ onResponse }: ChatPanelProps) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
  const [currentConvoId, setCurrentConvoId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [lastResponse, setLastResponse] = useState<ResponseData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* ---------- Init ---------- */

  useEffect(() => {
    const convos = loadConversations();
    if (convos.length === 0) {
      createNewConversation();
    } else {
      loadConversation(convos[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---------- Scroll helper ---------- */

  function scrollToBottom() {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }

  /* ---------- Conversation management ---------- */

  function saveCurrentState(
    convoId: string,
    currentEntries: ChatEntry[],
    currentLastResponse: ResponseData | null,
  ) {
    const convos = loadConversations();
    const idx = convos.findIndex((c) => c.id === convoId);
    if (idx === -1) return;

    const messages = currentEntries.map((e) => {
      if (e.role === "user") return { role: "user" as const, text: e.text };
      return { role: "nova" as const, data: e.data };
    });

    convos[idx].messages = messages;
    convos[idx]._lastResponse = currentLastResponse;

    const firstUser = messages.find((m) => m.role === "user");
    if (firstUser && firstUser.text) {
      convos[idx].title = firstUser.text.substring(0, 60);
    }

    saveConversations(convos);
  }

  function loadConversation(id: string) {
    const convos = loadConversations();
    const c = convos.find((cv) => cv.id === id);
    if (!c) return;

    setCurrentConvoId(id);

    const newEntries: ChatEntry[] = [];
    const newHistory: { role: string; content: string }[] = [];
    let resp: ResponseData | null = null;

    if (c.messages) {
      for (const m of c.messages) {
        if (m.role === "user") {
          newEntries.push({ role: "user", text: m.text || "" });
          newHistory.push({ role: "user", content: m.text || "" });
        } else if (m.role === "nova" && m.data) {
          newEntries.push({ role: "nova", text: m.data.response || "", data: m.data });
          newHistory.push({ role: "assistant", content: m.data.response || "" });
          resp = m.data;
        }
      }
    }

    setEntries(newEntries);
    setChatHistory(newHistory);
    setLastResponse(resp);
    onResponse(resp, {
      conversationId: id,
      messageIndex: newEntries.filter((e) => e.role === "nova").length - 1,
      userMessage: newHistory.filter((h) => h.role === "user").pop()?.content || "",
    });
  }

  const createNewConversation = useCallback(() => {
    const convos = loadConversations();
    const newConvo: Conversation = {
      id: "c_" + Date.now() + "_" + Math.random().toString(36).substring(2, 8),
      title: "New conversation",
      messages: [],
      created: Date.now(),
      _lastResponse: null,
    };
    convos.unshift(newConvo);
    saveConversations(convos);

    setCurrentConvoId(newConvo.id);
    setEntries([]);
    setChatHistory([]);
    setInputValue("");
    setSelectedFiles([]);
    setLastResponse(null);
    onResponse(null, { conversationId: newConvo.id, messageIndex: 0, userMessage: "" });
  }, [onResponse]);

  /* ---------- Send ---------- */

  async function send() {
    let msg = inputValue.trim();
    const hasFiles = selectedFiles.length > 0;
    if (!msg && !hasFiles) return;
    if (!msg && hasFiles) msg = "Analyze this document";

    const fileInfos = selectedFiles.map((f) => ({ name: f.name, size: f.size }));

    // Add user entry
    const userEntry: ChatEntry = { role: "user", text: msg, files: fileInfos.length ? fileInfos : undefined };
    const newEntries = [...entries, userEntry];
    setEntries(newEntries);
    setInputValue("");
    setIsThinking(true);
    scrollToBottom();

    // Build FormData
    const fd = new FormData();
    fd.append("message", msg);
    if (chatHistory.length) fd.append("history", JSON.stringify(chatHistory));
    for (const f of selectedFiles) fd.append("files", f);
    setSelectedFiles([]);

    try {
      const data = await sendPriceQuery(fd);

      const novaEntry: ChatEntry = { role: "nova", text: data.response || "", data };
      const updatedEntries = [...newEntries, novaEntry];

      const updatedHistory = [
        ...chatHistory,
        { role: "user", content: msg },
        { role: "assistant", content: data.response || "" },
      ];

      setEntries(updatedEntries);
      setChatHistory(updatedHistory);
      setLastResponse(data);
      setIsThinking(false);

      const novaCount = updatedEntries.filter((e) => e.role === "nova").length;
      onResponse(data, {
        conversationId: currentConvoId || "",
        messageIndex: novaCount - 1,
        userMessage: msg,
      });

      if (currentConvoId) {
        saveCurrentState(currentConvoId, updatedEntries, data);
      }
    } catch (err) {
      console.error("[Nova] Error:", err);
      setIsThinking(false);
      const errMsg = err instanceof Error ? err.message : String(err);
      const errorEntry: ChatEntry = {
        role: "nova",
        text: "Something went wrong. Please try again.",
        isError: true,
        errorDetail: errMsg,
      };
      setEntries([...newEntries, errorEntry]);
    }

    scrollToBottom();
  }

  /* ---------- Render ---------- */

  return (
    <div className="flex h-full">
      <ConversationSidebar
        currentId={currentConvoId}
        onSelect={(id) => {
          if (currentConvoId) saveCurrentState(currentConvoId, entries, lastResponse);
          loadConversation(id);
        }}
        onNewChat={() => {
          if (currentConvoId) saveCurrentState(currentConvoId, entries, lastResponse);
          createNewConversation();
        }}
      />

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* Welcome */}
          <div className="flex justify-start">
            <div className="glass-card p-6 rounded-xl max-w-[85%]">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white">
                  <MaterialIcon icon="precision_manufacturing" />
                </div>
                <span className="font-headline font-bold text-sm tracking-tight">
                  Nova Intelligence
                </span>
              </div>
              <p className="text-on-surface/90 leading-relaxed">
                Welcome back. I have updated market indices for oil &amp; gas
                compression assets. How can I assist with your valuation today?
              </p>
            </div>
          </div>

          {/* Messages */}
          {entries.map((entry, i) => {
            if (entry.role === "user") {
              return (
                <UserMessage key={i} text={entry.text} files={entry.files} />
              );
            }
            const isLatest = i === entries.length - 1 || (i === entries.length - 2 && isThinking);
            return (
              <NovaMessage
                key={i}
                text={entry.text}
                isLatest={isLatest}
                isError={entry.isError}
                errorDetail={entry.errorDetail}
              />
            );
          })}

          {isThinking && <ThinkingIndicator />}

          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="px-6 pb-6 pt-2 shrink-0">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={send}
            files={selectedFiles}
            onFilesSelected={(newFiles) =>
              setSelectedFiles((prev) => [...prev, ...newFiles])
            }
            onRemoveFile={(idx) =>
              setSelectedFiles((prev) => prev.filter((_, i) => i !== idx))
            }
            disabled={isThinking}
          />
        </div>
      </div>
    </div>
  );
}
