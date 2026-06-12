import { useState, useEffect } from "react";
import { useReport } from "../../hooks/useReport";
import type { ReportType, ReportFilters } from "../../hooks/useReport";

interface Props {
  open: boolean;
  onClose: () => void;
}

const REPORT_TYPES: {
  id: ReportType;
  label: string;
  icon: string;
  desc: string;
  filters: ("status" | "buyer" | "from_date" | "to_date" | "severity" | "category")[];
  statusOptions?: string[];
}[] = [
  {
    id: "summary",
    label: "Factory Summary",
    icon: "📊",
    desc: "Full factory overview: orders, shipments, inventory & lines in one document",
    filters: [],
  },
  {
    id: "orders",
    label: "Production Orders",
    icon: "📋",
    desc: "All production orders with progress, defects, and delivery dates",
    filters: ["status", "buyer", "from_date", "to_date"],
    statusOptions: ["Pending", "Cutting", "Sewing", "Finishing", "QC", "Packed", "Shipped", "Completed", "Cancelled"],
  },
  {
    id: "shipments",
    label: "Shipments",
    icon: "🚢",
    desc: "Shipment tracking with carrier, destination, ETA and linked orders",
    filters: ["status", "from_date", "to_date"],
    statusOptions: ["Pending", "In Transit", "Delivered", "Delayed", "Cancelled"],
  },
  {
    id: "inventory",
    label: "Inventory",
    icon: "📦",
    desc: "Raw material stock levels with low-stock and out-of-stock alerts",
    filters: ["status", "category"],
    statusOptions: ["In Stock", "Low Stock", "Out of Stock"],
  },
  {
    id: "quality",
    label: "Quality Control",
    icon: "🔍",
    desc: "Defect inspection records with severity breakdown and defect rates",
    filters: ["severity", "from_date", "to_date"],
    statusOptions: ["critical", "major", "minor"],
  },
  {
    id: "production-lines",
    label: "Production Lines",
    icon: "🏭",
    desc: "Line status, efficiency percentages, output and defect counts",
    filters: [],
  },
];

const FILTER_LABELS: Record<string, string> = {
  status:    "Status",
  buyer:     "Buyer (name)",
  from_date: "Date From",
  to_date:   "Date To",
  severity:  "Severity",
  category:  "Category",
};

export default function ReportModal({ open, onClose }: Props) {
  const { download, loading, error } = useReport();
  const [selected, setSelected]     = useState<ReportType>("summary");
  const [filters, setFilters]       = useState<ReportFilters>({});

  // Clear filters when report type changes
  useEffect(() => { setFilters({}); }, [selected]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const current = REPORT_TYPES.find(r => r.id === selected)!;

  const handleDownload = () => download(selected, filters);

  const setFilter = (key: string, val: string) =>
    setFilters(prev => ({ ...prev, [key]: val }));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/60
                      rounded-2xl shadow-2xl shadow-black/60 overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4
                        border-b border-slate-700/50 bg-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-teal-600
                            flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-white font-semibold text-sm">Download Report</h2>
              <p className="text-slate-500 text-xs">Branded PDF — ready to share with clients</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition p-1 rounded-lg
                       hover:bg-slate-700/50"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">

          {/* Report type grid */}
          <div>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">
              Select Report Type
            </p>
            <div className="grid grid-cols-3 gap-2">
              {REPORT_TYPES.map(rt => (
                <button
                  key={rt.id}
                  onClick={() => setSelected(rt.id)}
                  className={`flex items-start gap-2.5 p-3 rounded-xl border text-left
                              transition-all duration-150 group
                              ${selected === rt.id
                                ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                                : "border-slate-700/50 bg-slate-800/40 text-slate-300 hover:border-slate-600 hover:bg-slate-800"
                              }`}
                >
                  <span className="text-xl mt-0.5 shrink-0">{rt.icon}</span>
                  <div>
                    <p className="text-xs font-semibold leading-tight">{rt.label}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Description */}
          <div className="flex items-start gap-3 p-3 rounded-xl bg-slate-800/40
                          border border-slate-700/40">
            <span className="text-2xl">{current.icon}</span>
            <div>
              <p className="text-white text-sm font-medium">{current.label}</p>
              <p className="text-slate-400 text-xs mt-0.5">{current.desc}</p>
            </div>
          </div>

          {/* Filters */}
          {current.filters.length > 0 && (
            <div>
              <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">
                Filters <span className="text-slate-600 normal-case font-normal">(optional)</span>
              </p>
              <div className="grid grid-cols-2 gap-3">
                {current.filters.map(key => (
                  <div key={key}>
                    <label className="block text-slate-400 text-xs mb-1.5">
                      {FILTER_LABELS[key]}
                    </label>
                    {key === "status" || key === "severity" ? (
                      <select
                        value={filters[key as keyof ReportFilters] || ""}
                        onChange={e => setFilter(key, e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 text-white text-xs
                                   rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2
                                   focus:ring-blue-500/50 focus:border-blue-500/60 transition"
                      >
                        <option value="">All</option>
                        {current.statusOptions?.map(o => (
                          <option key={o} value={o}>{o}</option>
                        ))}
                      </select>
                    ) : key === "from_date" || key === "to_date" ? (
                      <input
                        type="date"
                        value={filters[key as keyof ReportFilters] || ""}
                        onChange={e => setFilter(key, e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 text-white text-xs
                                   rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2
                                   focus:ring-blue-500/50 focus:border-blue-500/60 transition
                                   [color-scheme:dark]"
                      />
                    ) : (
                      <input
                        type="text"
                        placeholder={key === "buyer" ? "e.g. H&M" : "e.g. Fabric"}
                        value={filters[key as keyof ReportFilters] || ""}
                        onChange={e => setFilter(key, e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 text-white text-xs
                                   rounded-lg px-3 py-2.5 placeholder-slate-600 focus:outline-none
                                   focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/60 transition"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-red-400 text-xs">{error}</p>
            </div>
          )}

          {/* Download button */}
          <button
            onClick={handleDownload}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl
                       bg-gradient-to-r from-blue-600 to-teal-600 text-white font-semibold
                       text-sm shadow-lg shadow-blue-500/20 hover:brightness-110
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10"
                    stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Generating PDF…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                </svg>
                Download {current.label} PDF
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
