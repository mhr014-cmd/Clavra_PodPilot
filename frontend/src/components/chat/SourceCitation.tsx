interface Source { document: string; page: number; similarity: number; doc_type?: string; }
export default function SourceCitation({ sources }: { sources: Source[] }) {
  return (
    <div className="mt-3 space-y-1">
      <p className="text-xs text-slate-500 font-medium">Sources</p>
      {sources.map((s, i) => (
        <div key={i} className="flex items-center gap-2 text-xs bg-teal-500/10
                                border border-teal-500/20 rounded-lg px-2.5 py-1.5">
          <svg className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-teal-300 truncate max-w-[180px]">{s.document}</span>
          <span className="text-slate-500">p.{s.page}</span>
          <span className="text-slate-600 ml-auto">{Math.round(s.similarity * 100)}%</span>
        </div>
      ))}
    </div>
  );
}
