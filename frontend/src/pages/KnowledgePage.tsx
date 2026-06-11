import { useState, useEffect, useRef } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface Doc { id: number; name: string; type: string; chunks: number; uploaded_at: string; }

const TYPE_META: Record<string, { label: string; color: string; icon: string }> = {
  policy:           { label: "Policy",       color: "bg-blue-500/20 text-blue-400 border-blue-500/30",     icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" },
  manual:           { label: "Manual",       color: "bg-purple-500/20 text-purple-400 border-purple-500/30", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
  sop:              { label: "SOP",          color: "bg-teal-500/20 text-teal-400 border-teal-500/30",     icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
  quality_standard: { label: "Quality Std", color: "bg-orange-500/20 text-orange-400 border-orange-500/30", icon: "M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" },
};

export default function KnowledgePage() {
  const [docs, setDocs]           = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType]     = useState("policy");
  const [message, setMessage]     = useState("");
  const [reindexing, setReindexing] = useState<number|null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadDocs(); }, []);

  const loadDocs = async () => {
    try {
      const res = await api.get("/knowledge/documents");
      setDocs(Array.isArray(res.data) ? res.data : []);
    } catch {}
  };

  const uploadFile = async (file: File) => {
    const ext = file.name.toLowerCase().split(".").pop() ?? "";
    if (!["pdf", "txt", "docx", "xlsx"].includes(ext)) {
      setMessage("✗ Only PDF, TXT, DOCX, and XLSX files are supported.");
      return;
    }
    setUploading(true);
    setMessage("");
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    try {
      await api.post(`/knowledge/upload?doc_type=${docType}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessage("✓ Document uploaded — AI is embedding it in the background.");
      loadDocs();
    } catch (err: any) {
      setMessage("✗ " + (err?.response?.data?.detail || "Upload failed"));
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  };

  const handleReindex = async (id: number) => {
    setReindexing(id);
    try {
      await api.post(`/knowledge/documents/${id}/reindex`);
      setMessage("✓ Re-indexing started — refresh in a few seconds.");
      setTimeout(loadDocs, 3000);
    } catch(err: any) {
      setMessage("✗ " + (err?.response?.data?.detail || "Re-index failed"));
    } finally {
      setReindexing(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this document from the knowledge base?")) return;
    try { await api.delete(`/knowledge/documents/${id}`); loadDocs(); } catch {}
  };

  return (
    <Layout>
      <div className="p-6 max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-blue-600
                          flex items-center justify-center shadow-lg shadow-teal-500/20">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Knowledge Base</h1>
            <p className="text-slate-400 text-sm">Upload PDFs, Word docs, or text files — the AI Copilot searches them for policy and manual questions</p>
          </div>
        </div>

        {/* Upload card */}
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-white font-semibold">Upload Document</h2>
            <select value={docType} onChange={e => setDocType(e.target.value)}
              className="bg-slate-700 border border-slate-600 text-white rounded-xl px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="policy">Policy</option>
              <option value="manual">Machine Manual</option>
              <option value="sop">SOP</option>
              <option value="quality_standard">Quality Standard</option>
            </select>
          </div>

          {/* Drag-drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !uploading && fileRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
                        transition-all duration-200
                        ${isDragging
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-slate-600 hover:border-slate-500 hover:bg-slate-700/20"}`}
          >
            <input ref={fileRef} type="file" accept=".pdf,.txt,.docx,.xlsx" className="hidden"
                   onChange={handleFileChange} disabled={uploading} />

            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                <p className="text-blue-400 text-sm font-medium">Uploading and embedding…</p>
                <p className="text-slate-500 text-xs">This may take a moment</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition
                                 ${isDragging ? "bg-blue-500/20" : "bg-slate-700/60"}`}>
                  <svg className={`w-7 h-7 transition ${isDragging ? "text-blue-400" : "text-slate-400"}`}
                       fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <div>
                  <p className="text-white text-sm font-semibold">
                    {isDragging ? "Drop your document here" : "Drag & drop a document here"}
                  </p>
                  <p className="text-slate-500 text-xs mt-1">or click to browse · PDF, TXT, DOCX, XLSX · max 20 MB</p>
                </div>
                <div className="flex flex-wrap justify-center gap-1.5 mt-1">
                  {Object.entries(TYPE_META).map(([k, v]) => (
                    <span key={k} className={`text-xs px-2 py-0.5 rounded-full border font-medium ${v.color}`}>
                      {v.label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {message && (
            <p className={`mt-3 text-sm ${message.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>
              {message}
            </p>
          )}
        </div>

        {/* Document list */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-white font-semibold">Indexed Documents</h2>
            <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-full border border-slate-700">
              {docs.length} {docs.length === 1 ? "document" : "documents"}
            </span>
          </div>

          {docs.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-700/60 rounded-2xl">
              <svg className="w-10 h-10 text-slate-700 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <p className="text-slate-500 text-sm">No documents uploaded yet</p>
              <p className="text-slate-600 text-xs mt-1">Upload a PDF, TXT, or DOCX above — AI will answer questions from it</p>
            </div>
          ) : (
            <div className="space-y-2">
              {docs.map(doc => {
                const meta = TYPE_META[doc.type] || TYPE_META.policy;
                return (
                  <div key={doc.id}
                    className="bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3.5
                               flex items-center gap-4 hover:border-slate-600 transition group">
                    <div className={`w-10 h-10 rounded-xl border flex items-center justify-center flex-shrink-0 ${meta.color}`}>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={meta.icon} />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">{doc.name}</p>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${meta.color}`}>
                          {meta.label}
                        </span>
                        <span className="text-slate-500 text-xs">{doc.chunks} chunks indexed</span>
                        <span className="text-slate-600 text-xs">
                          {new Date(doc.uploaded_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                      {/* Re-index — useful when doc shows 0 chunks */}
                      <button onClick={() => handleReindex(doc.id)} disabled={reindexing === doc.id}
                        title="Re-index this document"
                        className="text-slate-600 hover:text-teal-400 transition p-2 rounded-lg hover:bg-teal-500/10 disabled:opacity-40">
                        {reindexing === doc.id
                          ? <div className="w-4 h-4 border border-teal-400 border-t-transparent rounded-full animate-spin"/>
                          : <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                            </svg>
                        }
                      </button>
                      <button onClick={() => handleDelete(doc.id)}
                        title="Delete document"
                        className="text-slate-700 hover:text-red-400 transition p-2 rounded-lg hover:bg-red-500/10">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* How it works */}
        <div className="bg-slate-800/40 border border-slate-700/30 rounded-2xl p-5">
          <h3 className="text-white font-semibold mb-4 text-sm">How the AI uses these documents</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { step: "1", title: "Upload Document", desc: "PDFs, Word docs (.docx), text files (.txt), or Excel (.xlsx) — policies, SOPs, manuals, quality standards" },
              { step: "2", title: "AI Embeds",  desc: "Splits into chunks and creates semantic vector embeddings with pgvector" },
              { step: "3", title: "Smart Search", desc: "AI Copilot searches relevant sections when you ask policy or manual questions" },
            ].map(s => (
              <div key={s.step} className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/30
                                flex items-center justify-center flex-shrink-0 text-teal-400 text-xs font-bold">
                  {s.step}
                </div>
                <div>
                  <p className="text-white text-xs font-semibold">{s.title}</p>
                  <p className="text-slate-500 text-xs mt-0.5 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </Layout>
  );
}
