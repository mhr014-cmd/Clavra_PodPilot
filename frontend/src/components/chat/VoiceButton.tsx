interface VoiceButtonProps { isRecording: boolean; onToggle: () => void; disabled?: boolean; }
export default function VoiceButton({ isRecording, onToggle, disabled }: VoiceButtonProps) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`relative flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center
                  transition-all duration-200 disabled:opacity-40
                  ${isRecording
                    ? "bg-red-600 hover:bg-red-500 shadow-lg shadow-red-500/30"
                    : "bg-slate-700 hover:bg-slate-600"}`}
      title={isRecording ? "Stop recording" : "Start voice input"}
    >
      {isRecording && (
        <span className="absolute inset-0 rounded-xl bg-red-500 animate-ping opacity-40" />
      )}
      <svg className="w-5 h-5 text-white relative" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
      </svg>
    </button>
  );
}
