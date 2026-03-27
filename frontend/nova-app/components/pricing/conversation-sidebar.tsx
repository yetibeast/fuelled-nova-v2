"use client";

import { useState, useEffect } from "react";
import { MaterialIcon } from "@/components/ui/material-icon";
import { relativeTime } from "@/lib/utils";
import { getStoredUser, fetchConversations } from "@/lib/api";

function getStorageKey(): string {
  const user = getStoredUser();
  return user?.id ? `nova_conversations_${user.id}` : "nova_conversations";
}

export interface Conversation {
  id: string;
  title: string;
  messages: ConversationMessage[];
  created: number;
  created_at?: string;
  _lastResponse?: ResponseData | null;
}

export interface ConversationMessage {
  role: "user" | "nova";
  text?: string;
  data?: ResponseData | null;
}

export interface ResponseData {
  response?: string;
  structured?: Record<string, unknown>;
}

/* ── localStorage helpers (offline fallback) ── */

export function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(getStorageKey());
    const arr: Conversation[] = raw ? JSON.parse(raw) : [];
    arr.sort((a, b) => b.created - a.created);
    return arr;
  } catch {
    return [];
  }
}

export function saveConversations(convos: Conversation[]) {
  localStorage.setItem(getStorageKey(), JSON.stringify(convos));
}

/* ── API-backed loader (falls back to localStorage) ── */

export async function loadConversationsFromAPI(): Promise<Conversation[]> {
  try {
    const remote = await fetchConversations();
    if (Array.isArray(remote) && remote.length > 0) {
      return remote.map((r: { id: string; title: string; created_at?: string }) => ({
        id: r.id,
        title: r.title || "New conversation",
        messages: [],
        created: r.created_at ? new Date(r.created_at).getTime() : Date.now(),
        created_at: r.created_at,
      }));
    }
  } catch { /* fall back to local */ }
  return loadConversations();
}

interface ConversationSidebarProps {
  currentId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}

export function ConversationSidebar({
  currentId,
  onSelect,
  onNewChat,
}: ConversationSidebarProps) {
  const [collapsed, setCollapsed] = useState(true);
  const [convos, setConvos] = useState<Conversation[]>([]);

  useEffect(() => {
    loadConversationsFromAPI().then(setConvos);
  }, [currentId]);

  return (
    <div
      className="frosted-panel h-full flex flex-col shrink-0 transition-all duration-200 overflow-hidden"
      style={{ width: collapsed ? 48 : 260 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between h-[52px] px-2 shrink-0">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-10 h-10 flex items-center justify-center text-secondary hover:bg-white/10 rounded-lg transition-colors"
        >
          <MaterialIcon icon={collapsed ? "chevron_right" : "chevron_left"} />
        </button>
        {!collapsed && (
          <button
            onClick={onNewChat}
            className="flex items-center gap-2 bg-white/8 border border-secondary/25 text-secondary hover:bg-white/12 rounded-lg py-1.5 px-3 transition-colors"
          >
            <MaterialIcon icon="add" className="text-lg" />
            <span className="font-mono text-[11px] uppercase tracking-wider font-medium">
              New Chat
            </span>
          </button>
        )}
      </div>

      {/* List */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto">
          {convos.map((c) => {
            const active = c.id === currentId;
            return (
              <div
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={`py-[10px] px-4 cursor-pointer border-l-4 transition-colors ${
                  active
                    ? "border-l-secondary bg-white/5"
                    : "border-l-transparent hover:bg-white/5"
                }`}
              >
                <div className="truncate text-sm text-on-surface/90">
                  {c.title || "New conversation"}
                </div>
                <div className="font-mono text-[10px] text-on-surface/40 mt-0.5">
                  {relativeTime(c.created)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
