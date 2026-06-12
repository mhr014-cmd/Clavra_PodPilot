import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface Report {
  id: number; order_id?: number; line_id?: number;
  defect_type: string; defect_count: number; total_checked: number;
  defect_rate: number; severity: string; notes?: string; inspection_date: string;
}
interface OrderOption { id: number; order_no: string; buyer: string; }
interface LineOption  { id: number; line_name: string; }

const SEV_COLORS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  major:    "bg-orange-500/20 text-orange-400 border-orange-500/30",
  minor:    "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
};
const SEV_ICONS: Record<string, string> = { critical: "🔴", major: "🟠", minor: "🟡" };

type SevFilter = "all" | "minor" | "major" | "critical";

export default function QualityPage() {
  const [reports, setReports]       = useState<Report[]>([]);
  const [orders, setOrders]         = useState<OrderOption[]>([]);
  const [lines, setLines]           = useState<LineOption[]>([]);
  const [loading, setLoading]       = useState(true);
  const [showModal, setShowModal]   = useState(false);
  const [sevFilter, setSevFilter]   = useState<SevFilter>("all");
  const [search, setSearch]         = useState("");
  const [form, setForm] = useState({
    defect_type: "", defect_count: "", total_checked: "",
    severity: "minor", notes: "", line_id: "", order_id: "",
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg]       = useState("");

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [repRes, ordRes, lineRes] = await Promise.all([
        api.get("/quality/reports?limit=200"),
        api.get("/orders/", { params: { limit: 100 } }),
        api.get("/production-lines/"),
      ]);
      setReports(Array.isArray(repRes.data) ? repRes.data : []);
      setOrders(Array.isArray(ordRes.data) ? ordRes.data : []);
      setLines(Array.isArray(lineRes.data) ? lineRes.data : []);
    } catch {}
    finally { setLoading(false); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setMsg("");
    try {
      await api.post("/quality/reports", {
        defect_type:   form.defect_type,
        defect_count:  parseInt(form.defect_count)  || 0,
        total_checked: parseInt(form.total_checked) || 0,
        severity:      form.severity,
        notes:         form.notes,
        line_id:       form.line_id  ? parseInt(form.line_id)  : null,
        order_id:      form.order_id ? parseInt(form.order_id) : null,
      });
      setMsg("✓ Inspection logged");
      setShowModal(false);
      setForm({ defect_type:"", defect_count:"", total_checked:"", severity:"minor", notes:"", line_id:"", order_id:"" });
      loadAll();
    } catch (err: any) {
      setMsg("✗ " + (err?.response?.data?.detail || "Save failed"));
    } finally { setSaving(false); }
  };

  // KPIs
  const totalDefects  = reports.reduce((s, r) => s + r.defect_count, 0);
  const totalChecked  = reports.reduce((s, r) => s + r.total_checked, 0);
  const passRate      = totalChecked
    ? ((totalChecked - totalDefects) / totalChecked * 100).toFixed(1)
    : "100.0";
  const avgRate = reports.length
    ? (reports.reduce((s, r) => s + r.defect_rate, 0) / reports.length * 100).toFixed(2)
    : "0.00";
  const criticals = reports.filter(r => r.severity === "critical").length;

  // Defect type breakdown
  const defectByType: Record<string, { count: number; occurrences: number }> = {};
  for (const r of reports) {
    if (!defectByType[r.defect_type])
      defectByType[r.defect_type] = { count: 0, occurrences: 0 };
    defectByType[r.defect_type].count      += r.defect_count;
    defectByType[r.defect_type].occurrences += 1;
  }
  const sortedTypes = Object.entries(defectByType)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 7);
  const maxTypeCount = sortedTypes.length ? sortedTypes[0][1].count : 1;

  // Filtered table
  const filtered = reports
    .filter(r => sevFilter === "all" || r.severity === sevFilter)
    .filter(r => !search || r.defect_type.toLowerCase().includes(search.toLowerCase()));

  const kpis = [
    { label: "Inspections",    value: reports.length, icon: "📋", color: "text-blue-400",    ring: "border-blue-500/20 bg-blue-500/10"    },
    { label: "Total Defects",  value: totalDefects,   icon: "⚠️",  color: "text-red-400",     ring: "border-red-500/20 bg-red-500/10"     },
    { label: "Pass Rate",      value: `${passRate}%`, icon: "✅",  color: "text-emerald-400", ring: "border-emerald-500/20 bg-emerald-500/10" },
    { label: "Critical Issues",value: criticals,      icon: "🔴",  color: "text-red-500",     ring: "border-red-600/20 bg-red-600/10"     },
  ];

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-600 to-orange-600
                            flex items-center justify-center shadow-lg shadow-red-500/20">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806
                     3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946
                     3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806
                     3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946
                     3.42 3.42 0 013.138-3.138z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Quality Control</h1>
              <p className="text-slate-400 text-sm mt-0.5">Defect tracking and QC inspection management</p>
            </div>
          </div>
          <button
            onClick={() => { setMsg(""); setShowModal(true); }}
            className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-orange-600
                       hover:brightness-110 text-white text-sm font-semibold px-4 py-2.5
                       rounded-xl transition shadow-lg shadow-red-500/20"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
            </svg>
            Log Inspection
          </button>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {kpis.map(k => (
            <div key={k.label} className={`border rounded-2xl p-4 ${k.ring}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xl">{k.icon}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${k.ring} ${k.color}`}>
                  {reports.length > 0 ? "live" : "—"}
                </span>
              </div>
              <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
              <p className="text-xs text-slate-400 mt-0.5">{k.label}</p>
            </div>
          ))}
        </div>

        {/* Top Defect Types breakdown */}
        {sortedTypes.length > 0 && (
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold text-sm">Top Defect Types</h3>
              <span className="text-xs text-slate-500 bg-slate-700/50 px-2.5 py-1 rounded-full">
                {sortedTypes.length} types · {totalDefects.toLocaleString()} total defects
              </span>
            </div>
            <div className="space-y-3">
              {sortedTypes.map(([type, info]) => {
                const pct = Math.round(info.count / maxTypeCount * 100);
                const sharePct = totalDefects
                  ? Math.round(info.count / totalDefects * 100)
                  : 0;
                return (
                  <div key={type} className="grid grid-cols-[1fr_3fr_4rem] items-center gap-3">
                    <div>
                      <p className="text-xs text-white font-medium truncate">{type}</p>
                      <p className="text-[10px] text-slate-500">{info.occurrences} inspection{info.occurrences !== 1 ? "s" : ""}</p>
                    </div>
                    <div className="space-y-0.5">
                      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-red-500 to-orange-500 rounded-full transition-all duration-700"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-300 tabular-nums font-medium">{info.count}</p>
                      <p className="text-[10px] text-slate-500">{sharePct}%</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Table section */}
        <div>
          {/* Controls */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
            <div className="flex gap-1.5 flex-wrap">
              {(["all", "minor", "major", "critical"] as SevFilter[]).map(sev => (
                <button
                  key={sev}
                  onClick={() => setSevFilter(sev)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition font-medium capitalize
                    ${sevFilter === sev
                      ? "bg-slate-700 border-slate-500 text-white"
                      : "bg-slate-800/40 border-slate-700 text-slate-400 hover:border-slate-600"}`}
                >
                  {sev === "all"
                    ? `All (${reports.length})`
                    : `${SEV_ICONS[sev]} ${sev} (${reports.filter(r => r.severity === sev).length})`}
                </button>
              ))}
            </div>
            <input
              type="text"
              placeholder="Search defect type…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white placeholder-slate-500
                         rounded-xl px-3 py-2 text-sm w-full sm:w-56 focus:outline-none
                         focus:ring-2 focus:ring-red-500/40 focus:border-red-500/50 transition"
            />
          </div>

          {loading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin"/>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-14 border border-dashed border-slate-700/60 rounded-2xl">
              <p className="text-3xl mb-3">{reports.length === 0 ? "🔍" : "📭"}</p>
              <p className="text-slate-400 font-medium">
                {reports.length === 0 ? "No quality reports yet" : "No reports match your filter"}
              </p>
              <p className="text-slate-600 text-xs mt-1">
                {reports.length === 0
                  ? "Log your first inspection using the button above"
                  : "Try adjusting the severity filter or search term"}
              </p>
            </div>
          ) : (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/60">
                    {["Defect Type","Defects","Checked","Rate","Severity","Line / Order","Date"].map(h => (
                      <th key={h}
                        className="text-left text-slate-500 font-medium px-4 py-3 text-xs uppercase tracking-wide">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => (
                    <tr key={r.id}
                      className={`border-b border-slate-700/30 hover:bg-slate-700/20 transition
                                  ${i % 2 === 1 ? "bg-slate-800/30" : ""}`}>
                      <td className="px-4 py-3 text-white font-medium">{r.defect_type}</td>
                      <td className="px-4 py-3">
                        <span className="text-red-400 font-bold tabular-nums">{r.defect_count}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-300 tabular-nums">
                        {r.total_checked.toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`font-mono tabular-nums font-semibold
                          ${r.defect_rate * 100 >= 5 ? "text-red-400"
                            : r.defect_rate * 100 >= 2 ? "text-orange-400"
                            : "text-emerald-400"}`}>
                          {(r.defect_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full
                                          border font-medium ${SEV_COLORS[r.severity] || SEV_COLORS.minor}`}>
                          {SEV_ICONS[r.severity]} {r.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {r.line_id
                          ? lines.find(l => l.id === r.line_id)?.line_name ?? `Line ${r.line_id}`
                          : "—"}
                        {r.order_id
                          ? ` / ${orders.find(o => o.id === r.order_id)?.order_no ?? `#${r.order_id}`}`
                          : ""}
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-xs tabular-nums">
                        {new Date(r.inspection_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-3 border-t border-slate-700/40 flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Showing {filtered.length} of {reports.length} reports
                </span>
                <span className="text-xs text-slate-500">
                  Avg defect rate:{" "}
                  <span className="text-orange-400 font-mono font-semibold">{avgRate}%</span>
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Log Inspection Modal ───────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-base font-semibold text-white">Log Quality Inspection</h2>
                <p className="text-xs text-slate-500 mt-0.5">Record defect findings for a production run</p>
              </div>
              <button onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white transition p-1 rounded-lg hover:bg-slate-700/50">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">

                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Defect Type *</label>
                  <input
                    required
                    value={form.defect_type}
                    onChange={e => setForm(p => ({...p, defect_type: e.target.value}))}
                    placeholder="e.g. Stitching gap, Colour mismatch, Pilling"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Defect Count *</label>
                  <input required type="number" min="0"
                    value={form.defect_count}
                    onChange={e => setForm(p => ({...p, defect_count: e.target.value}))}
                    placeholder="0"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Total Checked *</label>
                  <input required type="number" min="1"
                    value={form.total_checked}
                    onChange={e => setForm(p => ({...p, total_checked: e.target.value}))}
                    placeholder="e.g. 500"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Severity</label>
                  <select value={form.severity}
                    onChange={e => setForm(p => ({...p, severity: e.target.value}))}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition">
                    <option value="minor">🟡 Minor</option>
                    <option value="major">🟠 Major</option>
                    <option value="critical">🔴 Critical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Production Line</label>
                  <select value={form.line_id}
                    onChange={e => setForm(p => ({...p, line_id: e.target.value}))}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition">
                    <option value="">— No line —</option>
                    {lines.map(l => (
                      <option key={l.id} value={String(l.id)}>{l.line_name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Production Order</label>
                  <select value={form.order_id}
                    onChange={e => setForm(p => ({...p, order_id: e.target.value}))}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50 transition">
                    <option value="">— No order —</option>
                    {orders.map(o => (
                      <option key={o.id} value={String(o.id)}>{o.order_no} · {o.buyer}</option>
                    ))}
                  </select>
                </div>

                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Notes</label>
                  <textarea
                    value={form.notes}
                    onChange={e => setForm(p => ({...p, notes: e.target.value}))}
                    placeholder="Optional inspector notes, batch number, shift info…"
                    rows={2}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl
                               px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50
                               resize-none transition"
                  />
                </div>
              </div>

              {msg && (
                <p className={`text-xs ${msg.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>{msg}</p>
              )}

              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setShowModal(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300
                             hover:bg-slate-700 transition text-sm font-medium">
                  Cancel
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-orange-600
                             hover:brightness-110 text-white text-sm font-semibold
                             transition disabled:opacity-50">
                  {saving ? "Saving…" : "Log Inspection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
