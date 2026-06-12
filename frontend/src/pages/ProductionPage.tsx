import { useState, useEffect, useCallback, useRef } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface Order {
  id: number;
  order_no: string;
  buyer: string;
  style: string;
  quantity: number;
  produced_qty: number;
  defect_qty: number;
  status: string;
  line_id: number | null;
  delivery_date: string | null;
  progress_pct: number;
  shipment_no: string | null;
  shipment_id: number | null;
  shipment_status: string | null;
  created_at: string | null;
}

interface ShipOption {
  id: number;
  shipment_no: string;
  status: string;
  destination: string | null;
}

const STATUSES = ["Pending", "Cutting", "Sewing", "Finishing", "QC", "Completed", "Cancelled"];

const STATUS_META: Record<string, { dot: string; bg: string; text: string }> = {
  Pending:    { dot: "bg-slate-400",   bg: "bg-slate-400/10",   text: "text-slate-400"   },
  Cutting:    { dot: "bg-blue-400",    bg: "bg-blue-400/10",    text: "text-blue-400"    },
  Sewing:     { dot: "bg-violet-400",  bg: "bg-violet-400/10",  text: "text-violet-400"  },
  Finishing:  { dot: "bg-amber-400",   bg: "bg-amber-400/10",   text: "text-amber-400"   },
  QC:         { dot: "bg-orange-400",  bg: "bg-orange-400/10",  text: "text-orange-400"  },
  Completed:  { dot: "bg-emerald-400", bg: "bg-emerald-400/10", text: "text-emerald-400" },
  Cancelled:  { dot: "bg-red-400",     bg: "bg-red-400/10",     text: "text-red-400"     },
};

const SHIP_STATUS_META: Record<string, { dot: string; text: string }> = {
  Pending:      { dot: "bg-slate-400",   text: "text-slate-400"   },
  "In Transit": { dot: "bg-blue-400",    text: "text-blue-400"    },
  Customs:      { dot: "bg-amber-400",   text: "text-amber-400"   },
  Delivered:    { dot: "bg-emerald-400", text: "text-emerald-400" },
  Delayed:      { dot: "bg-orange-400",  text: "text-orange-400"  },
  Cancelled:    { dot: "bg-red-400",     text: "text-red-400"     },
};

function StatusBadge({ status }: { status: string }) {
  const m = STATUS_META[status] ?? { dot: "bg-slate-400", bg: "bg-slate-400/10", text: "text-slate-300" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-current/20 ${m.bg} ${m.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {status}
    </span>
  );
}

function ShipBadge({ shipmentNo, status }: { shipmentNo: string; status: string }) {
  const m = SHIP_STATUS_META[status] ?? { dot: "bg-slate-400", text: "text-slate-400" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono border border-slate-600/50 bg-slate-700/50 ${m.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {shipmentNo}
    </span>
  );
}

function ProgressBar({ produced, total, status }: { produced: number; total: number; status: string }) {
  const rawPct = (produced / Math.max(total, 1)) * 100;
  // Minimum visible bar width of 1.5% so even tiny progress shows a sliver
  const barPct = produced > 0 ? Math.max(rawPct, 1.5) : 0;
  const displayPct = rawPct < 1 && produced > 0 ? "<1" : String(Math.round(rawPct));
  const color =
    status === "Completed" ? "bg-emerald-500" :
    status === "Cancelled" ? "bg-red-500/50"  :
    rawPct >= 75 ? "bg-blue-500" : rawPct >= 40 ? "bg-violet-500" : "bg-amber-500";
  return (
    <div className="flex items-center gap-2 min-w-[110px]">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${Math.min(barPct, 100)}%` }} />
      </div>
      <span className="text-xs text-slate-400 w-8 text-right tabular-nums">{displayPct}%</span>
    </div>
  );
}

function Spinner() {
  return <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin" />;
}

function EditIcon() {
  return (
    <svg className="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828a4 4 0 01-2.828 1.172H7v-2a4 4 0 011.172-2.828z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

export default function ProductionPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [updating, setUpdating] = useState<number | null>(null);
  const [form, setForm] = useState({ order_no: "", buyer: "", style: "", quantity: "", delivery_date: "" });
  const [saving, setSaving] = useState(false);

  // ── Inline editing state ──────────────────────────────────────────────────
  const [editProgress, setEditProgress] = useState<{ id: number; qty: string; defect: string } | null>(null);
  const [savingProgress, setSavingProgress] = useState<number | null>(null);

  const [editDate, setEditDate] = useState<{ id: number; value: string } | null>(null);
  const [savingDate, setSavingDate] = useState<number | null>(null);

  const [editShipment, setEditShipment] = useState<number | null>(null);
  const [shipOptions, setShipOptions] = useState<ShipOption[]>([]);
  const [loadingShipOpts, setLoadingShipOpts] = useState(false);
  const [savingShipment, setSavingShipment] = useState<number | null>(null);

  const dateInputRef = useRef<HTMLInputElement>(null);

  const fetchOrders = useCallback(async () => {
    try {
      setError(null);
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;
      const res = await api.get("/orders/", { params });
      setOrders(res.data);
    } catch {
      setError("Failed to load orders.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  // ── Status update ─────────────────────────────────────────────────────────
  const handleStatusChange = async (orderId: number, newStatus: string) => {
    setUpdating(orderId);
    try {
      await api.put(`/orders/${orderId}`, { status: newStatus });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: newStatus } : o));
    } catch {
      alert("Failed to update status.");
    } finally {
      setUpdating(null);
    }
  };

  // ── Progress save ─────────────────────────────────────────────────────────
  const saveProgress = async (orderId: number) => {
    if (!editProgress || editProgress.id !== orderId) return;
    const qty    = Math.max(0, parseInt(editProgress.qty)    || 0);
    const defect = Math.max(0, parseInt(editProgress.defect) || 0);
    setSavingProgress(orderId);
    try {
      const res = await api.put(`/orders/${orderId}`, { produced_qty: qty, defect_qty: defect });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, ...res.data } : o));
      setEditProgress(null);
    } catch {
      alert("Failed to update progress.");
    } finally {
      setSavingProgress(null);
    }
  };

  // ── Delivery date save ────────────────────────────────────────────────────
  const saveDate = async (orderId: number) => {
    if (!editDate || editDate.id !== orderId) return;
    setSavingDate(orderId);
    try {
      const isoDate = editDate.value ? new Date(editDate.value + "T00:00:00").toISOString() : null;
      const res = await api.put(`/orders/${orderId}`, { delivery_date: isoDate });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, delivery_date: res.data.delivery_date } : o));
      setEditDate(null);
    } catch {
      alert("Failed to update delivery date.");
    } finally {
      setSavingDate(null);
    }
  };

  // ── Shipment link ─────────────────────────────────────────────────────────
  const openShipmentPicker = async (orderId: number) => {
    setLoadingShipOpts(true);
    setEditShipment(orderId);
    try {
      const res = await api.get("/shipments/");
      setShipOptions(res.data);
    } catch {
      setEditShipment(null);
    } finally {
      setLoadingShipOpts(false);
    }
  };

  const linkShipment = async (orderId: number, shipmentId: number | null) => {
    setSavingShipment(orderId);
    try {
      const res = await api.put(`/orders/${orderId}/link-shipment`, { shipment_id: shipmentId });
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, ...res.data } : o));
      setEditShipment(null);
    } catch {
      alert("Failed to link shipment.");
    } finally {
      setSavingShipment(null);
    }
  };

  // ── Create order ──────────────────────────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        order_no: form.order_no, buyer: form.buyer,
        style: form.style, quantity: parseInt(form.quantity),
      };
      if (form.delivery_date) payload.delivery_date = new Date(form.delivery_date + "T00:00:00").toISOString();
      const res = await api.post("/orders/", payload);
      setOrders(prev => [res.data, ...prev]);
      setShowModal(false);
      setForm({ order_no: "", buyer: "", style: "", quantity: "", delivery_date: "" });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create order.");
    } finally {
      setSaving(false);
    }
  };

  const stats = {
    total:      orders.length,
    active:     orders.filter(o => !["Completed","Cancelled","Pending"].includes(o.status)).length,
    completed:  orders.filter(o => o.status === "Completed").length,
    shipLinked: orders.filter(o => !!o.shipment_no).length,
  };

  return (
    <Layout>
      <div className="p-6 max-w-[1400px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Production Orders</h1>
            <p className="text-sm text-slate-400 mt-0.5">Track manufacturing progress and linked shipments</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500
                       text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-blue-900/30"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Order
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Total Orders",    value: stats.total,      icon: "📋" },
            { label: "In Production",   value: stats.active,     icon: "⚙️" },
            { label: "Completed",       value: stats.completed,  icon: "✅" },
            { label: "Shipment Linked", value: stats.shipLinked, icon: "🚢" },
          ].map(c => (
            <div key={c.label} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-center gap-4">
              <span className="text-2xl">{c.icon}</span>
              <div>
                <p className="text-2xl font-bold text-white tabular-nums">{c.value}</p>
                <p className="text-xs text-slate-400">{c.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setLoading(true); }}
            className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-xl px-3 py-2
                       focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value="">All Statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <span className="text-slate-500 text-sm">{orders.length} order{orders.length !== 1 ? "s" : ""}</span>
          <span className="text-slate-600 text-xs ml-2">Click any cell to edit progress, date or shipment link</span>
        </div>

        {/* Table */}
        {error ? (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 text-sm">{error}</div>
        ) : loading ? (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : orders.length === 0 ? (
          <div className="text-center py-20 text-slate-500">
            <p className="text-4xl mb-3">📋</p>
            <p className="font-medium">No orders found</p>
            <p className="text-sm mt-1">Create your first production order to get started.</p>
          </div>
        ) : (
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 bg-slate-900/40">
                    {["Order No", "Buyer / Style", "Progress", "Delivery Date", "Shipment Link", "Status", "Update Status"].map(h => (
                      <th key={h} className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3.5 first:pl-5">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/30">
                  {orders.map(order => (
                    <tr key={order.id} className="hover:bg-slate-700/20 transition-colors">

                      {/* Order No */}
                      <td className="px-5 py-4">
                        <span className="font-mono font-semibold text-white">{order.order_no}</span>
                        <p className="text-xs text-slate-500 mt-0.5">Qty: {order.quantity.toLocaleString()}</p>
                      </td>

                      {/* Buyer / Style */}
                      <td className="px-4 py-4">
                        <p className="font-medium text-slate-200">{order.buyer}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{order.style}</p>
                      </td>

                      {/* ── Progress (click pencil to edit) ────────────── */}
                      <td className="px-4 py-4 min-w-[170px]">
                        {editProgress?.id === order.id ? (
                          <div className="space-y-2">
                            <ProgressBar
                              produced={parseInt(editProgress.qty) || 0}
                              total={order.quantity}
                              status={order.status}
                            />
                            <div className="flex items-center gap-1.5">
                              <input
                                type="number" min="0" max={order.quantity}
                                value={editProgress.qty}
                                onChange={e => setEditProgress(p => p ? { ...p, qty: e.target.value } : null)}
                                onKeyDown={e => {
                                  if (e.key === "Enter") saveProgress(order.id);
                                  if (e.key === "Escape") setEditProgress(null);
                                }}
                                autoFocus
                                placeholder="done pcs"
                                className="w-20 bg-slate-700 border border-blue-500/60 text-white text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                              <span className="text-slate-500 text-xs">/ {order.quantity.toLocaleString()}</span>
                              <button
                                onClick={() => saveProgress(order.id)}
                                disabled={savingProgress === order.id}
                                className="text-emerald-400 hover:text-emerald-300 transition p-0.5"
                              >
                                {savingProgress === order.id ? <Spinner /> : <CheckIcon />}
                              </button>
                              <button onClick={() => setEditProgress(null)} className="text-slate-400 hover:text-slate-300 transition p-0.5">
                                <XIcon />
                              </button>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <input
                                type="number" min="0"
                                value={editProgress.defect}
                                onChange={e => setEditProgress(p => p ? { ...p, defect: e.target.value } : null)}
                                placeholder="defect pcs"
                                className="w-20 bg-slate-700 border border-red-500/40 text-red-300 text-xs rounded-lg px-2 py-1 focus:outline-none"
                              />
                              <span className="text-red-400/60 text-xs">defect</span>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <ProgressBar produced={order.produced_qty} total={order.quantity} status={order.status} />
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <p className="text-xs text-slate-500 flex-1">
                                {order.produced_qty.toLocaleString()} / {order.quantity.toLocaleString()} pcs
                                {order.defect_qty > 0 && (
                                  <span className="text-red-400 ml-1.5">· {order.defect_qty} defect</span>
                                )}
                              </p>
                              <button
                                onClick={() => setEditProgress({ id: order.id, qty: String(order.produced_qty), defect: String(order.defect_qty) })}
                                title="Update progress"
                                className="flex-shrink-0 p-1 rounded-md text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 transition"
                              >
                                <EditIcon />
                              </button>
                            </div>
                          </div>
                        )}
                      </td>

                      {/* ── Delivery Date (click to edit) ──────────────── */}
                      <td className="px-4 py-4 min-w-[130px]">
                        {editDate?.id === order.id ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              ref={dateInputRef}
                              type="date"
                              value={editDate.value}
                              onChange={e => setEditDate(d => d ? { ...d, value: e.target.value } : null)}
                              onKeyDown={e => {
                                if (e.key === "Enter") saveDate(order.id);
                                if (e.key === "Escape") setEditDate(null);
                              }}
                              autoFocus
                              className="bg-slate-700 border border-blue-500/60 text-white text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                            <button
                              onClick={() => saveDate(order.id)}
                              disabled={savingDate === order.id}
                              className="text-emerald-400 hover:text-emerald-300 transition p-0.5"
                            >
                              {savingDate === order.id ? <Spinner /> : <CheckIcon />}
                            </button>
                            <button onClick={() => setEditDate(null)} className="text-slate-400 hover:text-slate-300 transition p-0.5">
                              <XIcon />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => {
                                const v = order.delivery_date ? order.delivery_date.split("T")[0] : "";
                                setEditDate({ id: order.id, value: v });
                              }}
                              className="text-left flex-1"
                            >
                              {order.delivery_date ? (() => {
                                const d = new Date(order.delivery_date);
                                const today = new Date();
                                const done = order.status === "Completed" || order.status === "Cancelled";
                                const overdue = !done && d < today;
                                const soon = !done && !overdue && (d.getTime() - today.getTime()) < 7 * 86400_000;
                                const fmt = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
                                return (
                                  <span className={`text-xs font-medium flex items-center gap-1 ${overdue ? "text-red-400" : soon ? "text-amber-400" : "text-slate-300"}`}>
                                    {overdue && <span title="Overdue">⚠</span>}
                                    {fmt}
                                  </span>
                                );
                              })() : (
                                <span className="text-slate-600 text-xs">— set date</span>
                              )}
                            </button>
                            <button
                              onClick={() => {
                                const v = order.delivery_date ? order.delivery_date.split("T")[0] : "";
                                setEditDate({ id: order.id, value: v });
                              }}
                              title="Set delivery date"
                              className="flex-shrink-0 p-1 rounded-md text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 transition"
                            >
                              <EditIcon />
                            </button>
                          </div>
                        )}
                      </td>

                      {/* ── Shipment Link (click to pick) ──────────────── */}
                      <td className="px-4 py-4 min-w-[140px]">
                        {editShipment === order.id ? (
                          <div className="flex items-center gap-1.5">
                            {loadingShipOpts ? (
                              <Spinner />
                            ) : (
                              <>
                                <select
                                  autoFocus
                                  defaultValue={order.shipment_id ?? ""}
                                  onChange={e => {
                                    const val = e.target.value;
                                    linkShipment(order.id, val ? parseInt(val) : null);
                                  }}
                                  disabled={savingShipment === order.id}
                                  className="bg-slate-700 border border-blue-500/60 text-slate-200 text-xs rounded-lg px-2 py-1.5 focus:outline-none max-w-[140px] disabled:opacity-50"
                                >
                                  <option value="">— Unlink —</option>
                                  {shipOptions.map(s => (
                                    <option key={s.id} value={s.id}>
                                      {s.shipment_no} · {s.status}
                                    </option>
                                  ))}
                                </select>
                                {savingShipment === order.id && <Spinner />}
                                <button onClick={() => setEditShipment(null)} className="text-slate-400 hover:text-slate-300 transition p-0.5">
                                  <XIcon />
                                </button>
                              </>
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <div className="flex-1">
                              {order.shipment_no && order.shipment_status ? (
                                <ShipBadge shipmentNo={order.shipment_no} status={order.shipment_status} />
                              ) : (
                                <span className="text-xs text-slate-600 italic">Not booked</span>
                              )}
                            </div>
                            <button
                              onClick={() => openShipmentPicker(order.id)}
                              title="Link shipment"
                              className="flex-shrink-0 p-1 rounded-md text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 transition"
                            >
                              <EditIcon />
                            </button>
                          </div>
                        )}
                      </td>

                      {/* Status badge */}
                      <td className="px-4 py-4">
                        <StatusBadge status={order.status} />
                      </td>

                      {/* Update status */}
                      <td className="px-4 py-4">
                        <div className="relative inline-block">
                          <select
                            value={order.status}
                            onChange={e => handleStatusChange(order.id, e.target.value)}
                            disabled={updating === order.id || order.status === "Cancelled"}
                            className="appearance-none bg-slate-700/50 border border-slate-600/60
                                       text-slate-300 text-xs rounded-lg pl-3 pr-7 py-1.5
                                       focus:outline-none focus:ring-1 focus:ring-blue-500/50
                                       disabled:opacity-40 cursor-pointer hover:bg-slate-700 transition"
                          >
                            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                          {updating === order.id && (
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-800/80 rounded-lg">
                              <Spinner />
                            </div>
                          )}
                        </div>
                      </td>

                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

      {/* New Order Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-base font-semibold text-white">New Production Order</h2>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Order No *</label>
                  <input value={form.order_no} onChange={e => setForm(f => ({ ...f, order_no: e.target.value }))}
                    placeholder="e.g. PO-010" required
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Buyer *</label>
                  <input value={form.buyer} onChange={e => setForm(f => ({ ...f, buyer: e.target.value }))}
                    placeholder="e.g. Zara Group" required
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Style / Description *</label>
                <input value={form.style} onChange={e => setForm(f => ({ ...f, style: e.target.value }))}
                  placeholder="e.g. Slim-fit Chino Trouser" required
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm
                             focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Quantity (pcs) *</label>
                  <input type="number" min="1" value={form.quantity}
                    onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                    placeholder="5000" required
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Delivery Date</label>
                  <input type="date" value={form.delivery_date}
                    onChange={e => setForm(f => ({ ...f, delivery_date: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-600 text-slate-300 rounded-xl px-3 py-2.5 text-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/50" />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">
                  Cancel
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition disabled:opacity-50">
                  {saving ? "Creating…" : "Create Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
