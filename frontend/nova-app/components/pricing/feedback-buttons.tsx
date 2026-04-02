"use client";

import { useState, useRef } from "react";
import { submitFeedback, getStoredUser } from "@/lib/api";

interface FeedbackButtonsProps {
  conversationId: string;
  messageIndex: number;
  userMessage: string;
  structuredData: Record<string, unknown>;
  responseText: string;
}

export function FeedbackButtons({
  conversationId,
  messageIndex,
  userMessage,
  structuredData,
  responseText,
}: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<"up" | "down" | null>(null);
  const [showComment, setShowComment] = useState(false);
  const commentRef = useRef<HTMLInputElement>(null);

  function sendFeedback(rating: "up" | "down", comment?: string) {
    const user = getStoredUser();
    submitFeedback({
      rating,
      comment,
      conversation_id: conversationId,
      message_index: messageIndex,
      user_message: userMessage,
      structured_data: structuredData,
      response_text: responseText,
      user_email: user?.email,
      user_name: user?.name,
    });
  }

  function handleUp() {
    if (submitted) return;
    setSubmitted("up");
    sendFeedback("up");
  }

  function handleDown() {
    if (submitted) return;
    setSubmitted("down");
    setShowComment(true);
    setTimeout(() => commentRef.current?.focus(), 50);
  }

  function submitComment() {
    const comment = commentRef.current?.value.trim() || "";
    sendFeedback("down", comment);
    setShowComment(false);
  }

  return (
    <div className="flex flex-col gap-2 pt-2">
      <div className="flex items-center gap-2">
        <button
          onClick={handleUp}
          disabled={submitted !== null}
          className={`flex items-center justify-center w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] transition-all text-sm ${
            submitted === "up"
              ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/10"
              : submitted
                ? "opacity-30 pointer-events-none text-on-surface/30"
                : "text-on-surface/30 hover:text-emerald-400 hover:border-emerald-400/30 hover:bg-emerald-400/10"
          }`}
          title="Good response"
        >
          &#x1F44D;
        </button>
        <button
          onClick={handleDown}
          disabled={submitted !== null}
          className={`flex items-center justify-center w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] transition-all text-sm ${
            submitted === "down"
              ? "text-primary border-primary/30 bg-primary/10"
              : submitted
                ? "opacity-30 pointer-events-none text-on-surface/30"
                : "text-on-surface/30 hover:text-primary hover:border-primary/30 hover:bg-primary/10"
          }`}
          title="Needs improvement"
        >
          &#x1F44E;
        </button>
        {submitted && !showComment && (
          <span className="text-[10px] font-mono text-on-surface/20 ml-1">
            Feedback saved
          </span>
        )}
      </div>
      {showComment && (
        <div className="flex items-center gap-2">
          <input
            ref={commentRef}
            type="text"
            placeholder="What was off?"
            maxLength={200}
            onKeyDown={(e) => e.key === "Enter" && submitComment()}
            className="recessed-input text-xs text-on-surface px-3 py-1.5 rounded-lg border border-white/10 flex-1 outline-none focus:border-secondary/40"
          />
          <button
            onClick={submitComment}
            className="text-[10px] font-mono text-secondary hover:text-white bg-secondary/10 hover:bg-secondary/20 px-3 py-1.5 rounded-lg border border-secondary/20 transition-all"
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}
