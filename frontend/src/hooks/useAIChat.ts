import { useState, useRef, useCallback } from "react";
import { useAuth } from "./useAuth";
import api from "../api/axios";
import type { Message } from "../components/chat/ChatBubble";
import { useChatStore } from "../store/chatStore";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

/**
 * Messages are stored in Zustand + localStorage so they survive navigation
 * and (optionally) page refresh within the same session.
 * Only isLoading is local state — it is purely UI, not persisted.
 */
export function useAIChat() {
  const { accessToken } = useAuth();
  const store = useChatStore();

  // isLoading is transient UI state — intentionally NOT persisted
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const timestamp = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const uid       = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  // ── Send via REST (fallback) ──────────────────────────────────────────────
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    store.addMessage({ id: uid(), role: "user", content: text, timestamp: timestamp() });
    setIsLoading(true);

    try {
      const res = await api.post("/ai/chat", {
        message: text,
        conversation_id: store.conversationId,
      });
      const d = res.data;
      if (d.conversation_id) store.setConversationId(d.conversation_id);

      store.addMessage({
        id: uid(), role: "assistant", content: d.message,
        intent: d.intent, confidence: d.confidence,
        actionType: d.action_type, sqlUsed: d.sql_used,
        sources: d.sources, timestamp: timestamp(),
        requiresConfirmation: d.requires_confirmation || false,
        pendingAction: d.pending_action || undefined,
      });
    } catch {
      store.addMessage({
        id: uid(), role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: timestamp(),
      });
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, store]);

  // ── Send via WebSocket (streaming) ────────────────────────────────────────
  const sendMessageWS = useCallback((text: string) => {
    if (!text.trim() || isLoading) return;

    store.addMessage({ id: uid(), role: "user", content: text, timestamp: timestamp() });
    setIsLoading(true);

    const aiId = uid();
    let accumulated = "";

    const ws = new WebSocket(`${WS_URL}/ai/ws/${store.conversationId || 0}`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ message: text, token: accessToken || "" }));
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);

      if (data.type === "intent") {
        store.addMessage({
          id: aiId, role: "assistant", content: "",
          intent: data.intent, confidence: data.confidence,
          actionType: data.action_type, timestamp: timestamp(),
        });
      } else if (data.type === "token") {
        accumulated += data.content;
        store.updateMessage(aiId, { content: accumulated });
      } else if (data.type === "done") {
        store.updateMessage(aiId, {
          sqlUsed:              data.sql_used,
          sources:              data.sources,
          requiresConfirmation: data.requires_confirmation || false,
          pendingAction:        data.pending_action || undefined,
        });
        setIsLoading(false);
        ws.close();
      } else if (data.type === "error") {
        setIsLoading(false);
      }
    };

    ws.onerror = () => { setIsLoading(false); };
    ws.onclose = () => { setIsLoading(false); };
  }, [isLoading, accessToken, store]);

  // ── Confirmation flow ─────────────────────────────────────────────────────
  const confirmAction = useCallback(async (action: { type: string; ref: string }, messageId: string) => {
    const original = store.messages.find(m => m.id === messageId)?.content ?? "";
    try {
      const res = await api.post("/ai/confirm", { action_type: action.type, ref: action.ref });
      store.updateMessage(messageId, {
        confirmationState: "confirmed",
        content: original + `\n\n✅ **Done:** ${res.data.message}`,
      });
    } catch (err: any) {
      store.updateMessage(messageId, {
        confirmationState: "confirmed",
        content: original + `\n\n❌ **Error:** ${err.response?.data?.detail || "Action failed."}`,
      });
    }
  }, [store]);

  const denyAction = useCallback((messageId: string) => {
    store.updateMessage(messageId, { confirmationState: "denied" });
  }, [store]);

  return {
    messages:      store.messages,
    isLoading,
    sendMessage,
    sendMessageWS,
    clearMessages: store.clearMessages,
    addMessage:    store.addMessage,
    confirmAction,
    denyAction,
  };
}
