import { create } from "zustand";
import type { Message } from "../components/chat/ChatBubble";

const STORAGE_KEY = "prodpilot_chat_v2";

interface ChatStore {
  messages:     Message[];
  conversationId: number | undefined;
  addMessage:   (msg: Message) => void;
  updateMessage:(id: string, patch: Partial<Message>) => void;
  clearMessages:() => void;
  setConversationId:(id: number) => void;
}

function load(): { messages: Message[]; conversationId: number | undefined } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { messages: [], conversationId: undefined };
}

function persist(state: Pick<ChatStore, "messages" | "conversationId">) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      messages:       state.messages,
      conversationId: state.conversationId,
    }));
  } catch {}
}

const saved = load();

export const useChatStore = create<ChatStore>((set, get) => ({
  messages:       saved.messages,
  conversationId: saved.conversationId,

  addMessage: (msg) => {
    const next = [...get().messages, msg];
    set({ messages: next });
    persist({ messages: next, conversationId: get().conversationId });
  },

  updateMessage: (id, patch) => {
    const next = get().messages.map(m => m.id === id ? { ...m, ...patch } : m);
    set({ messages: next });
    persist({ messages: next, conversationId: get().conversationId });
  },

  clearMessages: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ messages: [], conversationId: undefined });
  },

  setConversationId: (id) => {
    set({ conversationId: id });
    persist({ messages: get().messages, conversationId: id });
  },
}));
