interface IntentBadgeProps {
  intent: string;
  confidence: number;
  actionType: string;
}

const ACTION_CONFIG: Record<string, { label: string; dot: string; bg: string; text: string; border: string }> = {
  business_action:    { label: "Action",  dot: "bg-orange-400", bg: "bg-orange-500/15", text: "text-orange-300", border: "border-orange-500/30" },
  analytics_question: { label: "SQL",     dot: "bg-blue-400",   bg: "bg-blue-500/15",   text: "text-blue-300",   border: "border-blue-500/30"   },
  knowledge_question: { label: "Docs",    dot: "bg-teal-400",   bg: "bg-teal-500/15",   text: "text-teal-300",   border: "border-teal-500/30"   },
  vision_request:     { label: "Vision",  dot: "bg-purple-400", bg: "bg-purple-500/15", text: "text-purple-300", border: "border-purple-500/30" },
  unknown:            { label: "?",       dot: "bg-slate-500",  bg: "bg-slate-500/10",  text: "text-slate-400",  border: "border-slate-600/40"  },
};

export default function IntentBadge({ intent, confidence, actionType }: IntentBadgeProps) {
  const cfg = ACTION_CONFIG[actionType] || ACTION_CONFIG.unknown;
  const pct = Math.round(confidence * 100);
  const confColor = pct >= 85 ? "text-emerald-400" : pct >= 65 ? "text-yellow-400" : "text-red-400";

  return (
    <div className={`inline-flex items-center gap-2 mb-2.5 px-2.5 py-1.5 rounded-lg border ${cfg.bg} ${cfg.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <span className={`text-xs font-semibold ${cfg.text}`}>{cfg.label}</span>
      <span className="text-xs text-slate-500 font-mono truncate max-w-[160px]">
        {intent.replace(/_/g, " ")}
      </span>
      <span className={`text-xs font-mono font-medium ${confColor}`}>
        {pct}%
      </span>
    </div>
  );
}
