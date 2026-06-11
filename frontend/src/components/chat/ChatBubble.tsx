import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import IntentBadge from "./IntentBadge";
import SqlViewPanel from "./SqlViewPanel";
import SourceCitation from "./SourceCitation";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  confidence?: number;
  actionType?: string;
  sqlUsed?: string;
  sources?: any[];
  timestamp: string;
  requiresConfirmation?: boolean;
  pendingAction?: { type: string; ref: string; details?: any };
  confirmationState?: "pending" | "confirmed" | "denied";
}

interface ChatBubbleProps {
  message: Message;
  onSpeak?: (text: string) => void;
  onConfirm?: (action: { type: string; ref: string }) => void;
  onDeny?: (messageId: string) => void;
}

const mdComponents = {
  p:      ({ children }: any) => <p className="mb-2 last:mb-0 leading-relaxed text-slate-200">{children}</p>,
  strong: ({ children }: any) => <strong className="font-semibold text-white">{children}</strong>,
  em:     ({ children }: any) => <em className="italic text-slate-300">{children}</em>,
  ul:     ({ children }: any) => <ul className="my-2 space-y-1 pl-1">{children}</ul>,
  ol:     ({ children }: any) => <ol className="my-2 space-y-1 pl-1 list-decimal list-inside">{children}</ol>,
  li:     ({ children }: any) => (
    <li className="flex items-start gap-2 leading-relaxed text-slate-300">
      <span className="text-blue-400 mt-0.5 flex-shrink-0">›</span>
      <span>{children}</span>
    </li>
  ),
  code:   ({ children }: any) => (
    <code className="bg-slate-900/80 border border-slate-700 px-1.5 py-0.5 rounded text-xs text-blue-300 font-mono">
      {children}
    </code>
  ),
  pre:    ({ children }: any) => (
    <pre className="bg-slate-900/80 border border-slate-700 rounded-lg p-3 my-2 overflow-x-auto text-xs text-slate-300 font-mono">
      {children}
    </pre>
  ),
  h2: ({ children }: any) => <h2 className="font-bold text-white text-sm mt-3 mb-1.5 border-b border-slate-700/50 pb-1">{children}</h2>,
  h3: ({ children }: any) => <h3 className="font-semibold text-white text-sm mt-2.5 mb-1">{children}</h3>,
  h4: ({ children }: any) => <h4 className="font-medium text-blue-300 text-xs mt-2 mb-1 uppercase tracking-wide">{children}</h4>,
  hr:  () => <hr className="border-slate-700/50 my-2" />,
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-2 border-blue-500/50 pl-3 my-2 text-slate-400 italic text-xs">
      {children}
    </blockquote>
  ),
};

export default function ChatBubble({ message, onSpeak, onConfirm, onDeny }: ChatBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[72%]">
          <div className="bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-lg shadow-blue-900/30">
            <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
          <p className="text-slate-600 text-xs mt-1 text-right pr-1">{message.timestamp}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-3 gap-2.5">
      {/* AI avatar */}
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-teal-500
                      flex items-center justify-center flex-shrink-0 mt-1 shadow-md shadow-blue-900/30">
        <span className="text-white text-[10px] font-bold">AI</span>
      </div>

      <div className="max-w-[78%] min-w-0">
        <p className="text-xs text-slate-500 font-medium mb-1">ProdPilot</p>

        <div className="bg-slate-800/90 border border-slate-700/60 rounded-2xl rounded-tl-sm px-4 py-3 shadow-lg">
          {/* Intent badge */}
          {message.intent && message.confidence !== undefined && message.actionType && (
            <IntentBadge
              intent={message.intent}
              confidence={message.confidence}
              actionType={message.actionType}
            />
          )}

          {/* Message text with markdown */}
          <div className="text-slate-200 text-sm min-w-0">
            {message.content ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {message.content}
              </ReactMarkdown>
            ) : (
              <span className="text-slate-500 italic text-xs">Thinking…</span>
            )}
          </div>

          {/* SQL panel */}
          {message.sqlUsed && <SqlViewPanel sql={message.sqlUsed} />}

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <SourceCitation sources={message.sources} />
          )}

          {/* Confirmation action buttons */}
          {message.requiresConfirmation && message.pendingAction && (
            <div className="mt-3 pt-3 border-t border-slate-700/40">
              {message.confirmationState === "confirmed" ? (
                <div className="flex items-center gap-2 text-emerald-400 text-xs">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Action confirmed and executed
                </div>
              ) : message.confirmationState === "denied" ? (
                <div className="flex items-center gap-2 text-slate-500 text-xs">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Action cancelled — no changes made
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onConfirm?.(message.pendingAction!)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                               bg-red-500/20 border border-red-500/40 text-red-300
                               hover:bg-red-500/30 transition"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Yes, proceed
                  </button>
                  <button
                    onClick={() => onDeny?.(message.id)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                               bg-slate-700/50 border border-slate-600 text-slate-300
                               hover:bg-slate-700 transition"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    No, cancel
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-700/40">
            <p className="text-slate-600 text-xs">{message.timestamp}</p>
            {onSpeak && (
              <button
                onClick={() => onSpeak(message.content)}
                className="text-slate-600 hover:text-blue-400 transition p-1 rounded-lg hover:bg-slate-700/50"
                title="Read aloud"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15.536 8.464a5 5 0 010 7.072M12 6v12m0 0l-3-3m3 3l3-3" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
