import { useState, useRef, useEffect, useCallback } from "react";
import Layout from "../components/Layout";
import ChatBubble from "../components/chat/ChatBubble";
import TypingIndicator from "../components/chat/TypingIndicator";
import VoiceButton from "../components/chat/VoiceButton";
import ImageUploadZone from "../components/chat/ImageUploadZone";
import type { Message } from "../components/chat/ChatBubble";
import { useAIChat } from "../hooks/useAIChat";
import { useVoice } from "../hooks/useVoice";
import { useAuth } from "../hooks/useAuth";
import api from "../api/axios";

const QUICK_CHIPS = [
  { text: "Give me a factory summary",          icon: "🏭", color: "blue"   },
  { text: "How are my orders?",                 icon: "📋", color: "orange" },
  { text: "Any shipments going out?",           icon: "🚢", color: "orange" },
  { text: "Am I running low on anything?",      icon: "📦", color: "orange" },
  { text: "Create order for H&M, 5000 pieces of Summer Dress", icon: "➕", color: "teal" },
  { text: "Move PO-001 to Cutting",             icon: "🔄", color: "teal"   },
  { text: "Book shipment to Hamburg via Maersk",icon: "🚢", color: "teal"   },
  { text: "Log 30 defects for PO-001, type: stain", icon: "⚠️", color: "orange" },
  { text: "How efficient is production?",       icon: "📊", color: "blue"   },
  { text: "What can you help me with?",         icon: "💡", color: "blue"   },
];

const CHIP_COLORS: Record<string, string> = {
  orange: "border-orange-500/30 text-orange-300 hover:bg-orange-500/10",
  blue:   "border-blue-500/30   text-blue-300   hover:bg-blue-500/10",
  teal:   "border-teal-500/30   text-teal-300   hover:bg-teal-500/10",
};

const WELCOME_MSG: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! 👋 I'm your **ProdPilot AI Copilot** — full factory control by voice or text.\n\n" +
    "**📋 Orders** — *'Show my orders'*, *'PO-001 status'*, *'Cancel PO-002'*\n" +
    "**➕ Create** — *'Create order for H&M, 5000 pcs of Summer Dress'*\n" +
    "**🔄 Update** — *'Move PO-001 to Cutting'*, *'Mark PO-002 as Completed'*\n" +
    "**🚢 Shipments** — *'Any shipments going out?'*, *'Book shipment to Hamburg'*\n" +
    "**📦 Inventory** — *'Am I low on anything?'*\n" +
    "**⚠️ Quality** — *'Log 30 defects for PO-001, type: stain'*\n" +
    "**📄 Documents** — *'Fabric Inspection SOP'*, *'Show quality policy'*\n\n" +
    "Works with **voice** 🎙 too — just press the mic button and speak naturally.",
  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
};

export default function AICopilotPage() {
  const { user } = useAuth();
  const { messages, isLoading, sendMessage, sendMessageWS, clearMessages, addMessage, confirmAction, denyAction } = useAIChat();
  const { isRecording, isPlaying, transcript, clearTranscript, toggleRecording, playText } = useVoice();

  const [input, setInput]         = useState("");
  const [useWS, setUseWS]         = useState(true);
  const [apiKeyOk, setApiKeyOk]   = useState<boolean | null>(null);
  const [visionModel, setVision]  = useState<string | null>(null);
  const [imageLoading, setImgLoad] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const autoSentRef = useRef<string>("");
  useEffect(() => {
    if (!transcript) return;
    setInput(transcript);
    // Auto-send once recording has stopped and we have a final transcript
    if (!isRecording && transcript.trim() && autoSentRef.current !== transcript) {
      autoSentRef.current = transcript;
      const timer = setTimeout(() => {
        handleSend(transcript);
        setInput("");
        clearTranscript();
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [transcript, isRecording]);

  useEffect(() => {
    api.get("/ai/health")
      .then((r) => {
        setApiKeyOk(r.data?.openai === true);
        setVision(r.data?.vision ?? null);
      })
      .catch(() => setApiKeyOk(false));
  }, []);

  const handleSend = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    if (useWS) sendMessageWS(msg);
    else sendMessage(msg);
    setInput("");
    inputRef.current?.focus();
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleImageUpload = async (file: File) => {
    const ts  = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;

    addMessage({ id: uid(), role: "user",
      content: `📸 **Image uploaded for analysis:** \`${file.name}\``, timestamp: ts() });
    setImgLoad(true);

    const form = new FormData();
    form.append("image", file);
    try {
      const res = await api.post("/ai/vision/analyze", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const d = res.data;
      let content = `**Vision Analysis — \`${file.name}\`**\n\n`;
      if (d.summary)         content += `${d.summary}\n\n`;
      if (d.findings?.length) {
        content += `**Findings:**\n${(d.findings as string[]).map(f => `- ${f}`).join("\n")}\n\n`;
      }
      if (d.severity)        content += `**Severity:** ${d.severity}\n\n`;
      if (d.recommendations?.length) {
        content += `**Recommendations:**\n${(d.recommendations as string[]).map(r => `- ${r}`).join("\n")}`;
      }
      addMessage({ id: uid(), role: "assistant", content, timestamp: ts() });
    } catch {
      addMessage({ id: uid(), role: "assistant",
        content: "❌ Image analysis failed. A valid OpenAI API key is required for Vision.",
        timestamp: ts() });
    } finally {
      setImgLoad(false);
    }
  };

  return (
    <Layout>
      <div className="flex flex-col h-[calc(100vh-64px)] max-w-4xl mx-auto">

        {/* ── Header ───────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700/50 bg-slate-900/40 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-teal-600
                            flex items-center justify-center shadow-lg shadow-blue-500/25">
              <svg className="w-4.5 h-4.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white">ProdPilot AI Copilot</h1>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`w-1.5 h-1.5 rounded-full ${apiKeyOk ? "bg-emerald-400" : "bg-yellow-400"}`} />
                <p className="text-xs text-slate-500">
                  {apiKeyOk === null ? "Checking…"
                    : apiKeyOk
                      ? `GPT-4o · 14 intents · Vision: GPT-4o`
                      : `Keyword mode · Vision: ${visionModel && visionModel !== "unavailable" ? visionModel.split(":")[0] : "unavailable"}`
                  }
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setUseWS(!useWS)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition font-medium
                ${useWS ? "border-blue-500/40 text-blue-400 bg-blue-500/10"
                        : "border-slate-600 text-slate-400 bg-slate-800"}`}
            >
              {useWS ? "⚡ Stream" : "REST"}
            </button>
            {messages.length > 0 && (
              <button
                onClick={clearMessages}
                className="text-xs px-3 py-1.5 rounded-lg border border-slate-600
                           text-slate-400 hover:bg-slate-700/60 transition"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* ── Messages ─────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-1 scroll-smooth">

          {/* Always-visible welcome message */}
          <ChatBubble message={WELCOME_MSG} onSpeak={playText} onConfirm={() => {}} onDeny={() => {}} />

          {/* Message thread */}
          {messages.map((msg) => (
            <ChatBubble
              key={msg.id}
              message={msg}
              onSpeak={playText}
              onConfirm={(action) => confirmAction(action, msg.id)}
              onDeny={(id) => denyAction(id)}
            />
          ))}

          {(isLoading || imageLoading) && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Quick chips (always visible) ─────────────────────────── */}
        <div className="px-4 pb-2">
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {QUICK_CHIPS.map((c) => (
              <button
                key={c.text}
                onClick={() => handleSend(c.text)}
                disabled={isLoading}
                className={`flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full
                            border bg-slate-800/60 transition disabled:opacity-40
                            hover:border-slate-500 ${CHIP_COLORS[c.color]}`}
              >
                <span>{c.icon}</span>
                <span className="whitespace-nowrap">{c.text}</span>
              </button>
            ))}
          </div>
        </div>

        {/* ── Input bar ────────────────────────────────────────────── */}
        <div className="border-t border-slate-700/50 px-4 py-3 bg-slate-900/40 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <VoiceButton isRecording={isRecording} onToggle={toggleRecording} disabled={isLoading} />
            <ImageUploadZone onImageSelect={handleImageUpload} />
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder={isRecording ? "🎙 Listening… speak now, auto-sends when done" : "Ask anything about your factory…"}
              disabled={isLoading}
              className="flex-1 bg-slate-800 border border-slate-700 text-white placeholder-slate-500
                         rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2
                         focus:ring-blue-500/50 focus:border-blue-500/60 transition
                         disabled:opacity-50"
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-600 to-teal-600
                         hover:brightness-110 disabled:from-slate-700 disabled:to-slate-700
                         disabled:opacity-40 flex items-center justify-center transition
                         flex-shrink-0 shadow-lg shadow-blue-500/20"
            >
              <svg className="w-4.5 h-4.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>

          {(isRecording || isPlaying) && (
            <p className="text-center text-xs mt-2">
              {isRecording && <span className="text-red-400 animate-pulse">🎙 Recording… speak now — auto-sends on silence</span>}
              {isPlaying   && <span className="text-blue-400">🔊 Playing response…</span>}
            </p>
          )}
        </div>

      </div>
    </Layout>
  );
}
