import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import api from "../api/axios";

const COLORS = ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#06b6d4"];

interface Stats {
  orders: number; shipments: number; materials: number;
  runningLines: number; lowStock: number; revenue: number;
}

const KPI_CONFIG = [
  { key: "orders",       label: "Total Orders",    unit: "",   color: "blue",   icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
  { key: "shipments",    label: "Shipments",       unit: "",   color: "teal",   icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" },
  { key: "materials",    label: "Materials",       unit: "",   color: "purple", icon: "M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" },
  { key: "runningLines", label: "Active Lines",    unit: "",   color: "green",  icon: "M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" },
  { key: "lowStock",     label: "Low Stock",       unit: "",   color: "yellow", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" },
  { key: "revenue",      label: "Est. Revenue",   unit: "$",  color: "orange", icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
];

const COLOR_MAP: Record<string, { bg: string; border: string; icon: string; text: string; glow: string }> = {
  blue:   { bg: "bg-blue-500/10",   border: "border-blue-500/30",   icon: "text-blue-400",   text: "text-blue-300",   glow: "shadow-blue-500/20" },
  teal:   { bg: "bg-teal-500/10",   border: "border-teal-500/30",   icon: "text-teal-400",   text: "text-teal-300",   glow: "shadow-teal-500/20" },
  purple: { bg: "bg-purple-500/10", border: "border-purple-500/30", icon: "text-purple-400", text: "text-purple-300", glow: "shadow-purple-500/20" },
  green:  { bg: "bg-green-500/10",  border: "border-green-500/30",  icon: "text-green-400",  text: "text-green-300",  glow: "shadow-green-500/20" },
  yellow: { bg: "bg-yellow-500/10", border: "border-yellow-500/30", icon: "text-yellow-400", text: "text-yellow-300", glow: "shadow-yellow-500/20" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/30", icon: "text-orange-400", text: "text-orange-300", glow: "shadow-orange-500/20" },
};

export default function DashboardPage() {
  const [stats, setStats]         = useState<Stats>({ orders:0, shipments:0, materials:0, runningLines:0, lowStock:0, revenue:0 });
  const [orderData, setOrderData] = useState<any[]>([]);
  const [lineData,  setLineData]  = useState<any[]>([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => { loadDashboard(); }, []);

  const loadDashboard = async () => {
    try {
      const [ordersRes, shipmentsRes, inventoryRes, linesRes, analyticsRes] = await Promise.all([
        api.get("/orders/"),
        api.get("/shipments/"),
        api.get("/inventory/"),
        api.get("/production-lines/"),
        api.get("/analytics/dashboard").catch(() => ({ data: {} })),
      ]);

      const orders    = Array.isArray(ordersRes.data)    ? ordersRes.data    : [];
      const shipments = Array.isArray(shipmentsRes.data) ? shipmentsRes.data : [];
      const inventory = Array.isArray(inventoryRes.data) ? inventoryRes.data : [];
      const lines     = Array.isArray(linesRes.data)     ? linesRes.data     : [];
      const analytics = analyticsRes.data || {};

      setStats({
        orders:      orders.length,
        shipments:   shipments.length,
        materials:   inventory.length,
        runningLines: lines.filter((l: any) => l.status === "Running").length,
        lowStock:    inventory.filter((i: any) => i.status === "Low Stock").length,
        revenue:     analytics.revenue || 0,
      });

      const statusCounts: Record<string, number> = {};
      orders.forEach((o: any) => { statusCounts[o.status] = (statusCounts[o.status] || 0) + 1; });
      setOrderData(Object.entries(statusCounts).map(([name, value]) => ({ name, value })));

      setLineData(lines.slice(0, 6).map((l: any) => ({
        name: l.line_name?.substring(0, 10) || `Line ${l.id}`,
        efficiency: Math.round((l.efficiency || 0) * 100) / 100,
        output: l.actual_output || 0,
      })));
    } catch (err) {
      console.error("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const getStatValue = (key: string, unit: string) => {
    if (loading) return "—";
    const val = (stats as any)[key];
    return unit === "$" ? `$${Number(val).toLocaleString()}` : val;
  };

  return (
    <Layout>
      <div className="p-6 space-y-6">

        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Factory Dashboard</h1>
            <p className="text-slate-400 text-sm mt-0.5">Live overview of your manufacturing operations</p>
          </div>
          <Link to="/ai-copilot"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                       bg-gradient-to-r from-blue-600 to-teal-600
                       text-white text-sm font-semibold shadow-lg shadow-blue-500/25
                       hover:shadow-blue-500/40 hover:brightness-110 transition-all">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Open AI Copilot
          </Link>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {KPI_CONFIG.map(({ key, label, unit, color, icon }) => {
            const c = COLOR_MAP[color];
            return (
              <div key={key}
                className={`relative rounded-2xl p-4 border ${c.bg} ${c.border} shadow-lg ${c.glow}`}>
                <div className={`w-9 h-9 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center mb-3`}>
                  <svg className={`w-5 h-5 ${c.icon}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
                  </svg>
                </div>
                <p className="text-slate-400 text-xs font-medium mb-1">{label}</p>
                <p className={`text-2xl font-bold ${c.text}`}>{getStatValue(key, unit)}</p>
              </div>
            );
          })}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Line Efficiency (%)</h3>
              <span className="text-xs text-slate-500 bg-slate-700/50 px-2.5 py-1 rounded-full">Top 6 lines</span>
            </div>
            {lineData.length === 0 ? (
              <div className="h-52 flex flex-col items-center justify-center text-slate-500 text-sm gap-2">
                <svg className="w-8 h-8 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                No production line data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={208}>
                <BarChart data={lineData} barSize={28}>
                  <XAxis dataKey="name" stroke="#334155" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis stroke="#334155" tick={{ fill: "#94a3b8", fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", color: "#f1f5f9", fontSize: 12 }}
                    cursor={{ fill: "rgba(148,163,184,0.05)" }}
                  />
                  <Bar dataKey="efficiency" radius={[6,6,0,0]}>
                    {lineData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Orders by Status</h3>
              <span className="text-xs text-slate-500 bg-slate-700/50 px-2.5 py-1 rounded-full">
                {stats.orders} total
              </span>
            </div>
            {orderData.length === 0 ? (
              <div className="h-52 flex flex-col items-center justify-center text-slate-500 text-sm gap-2">
                <svg className="w-8 h-8 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                </svg>
                No order data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart margin={{ top: 18, right: 40, bottom: 5, left: 40 }}>
                  <Pie data={orderData} cx="50%" cy="45%" innerRadius={46} outerRadius={68}
                       dataKey="value" paddingAngle={3}
                       label={({ percent }) => `${Math.round(percent * 100)}%`}
                       labelLine={{ stroke: "#475569", strokeWidth: 1 }}>
                    {orderData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "10px", color: "#f1f5f9", fontSize: 12 }} />
                  <Legend wrapperStyle={{ color: "#94a3b8", fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* AI Copilot promo + quick actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          {/* AI Copilot card */}
          <div className="lg:col-span-1 relative rounded-2xl overflow-hidden border border-blue-500/20 bg-gradient-to-br from-blue-950/60 via-slate-900/80 to-teal-950/40 p-5">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -translate-y-8 translate-x-8 pointer-events-none" />
            <div className="relative">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-600 to-teal-600
                              flex items-center justify-center shadow-lg shadow-blue-500/30 mb-3">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-white font-semibold mb-1">AI Copilot</h3>
              <p className="text-slate-400 text-xs leading-relaxed mb-4">
                Ask anything — orders, shipments, inventory, quality. Intent-aware AI with SQL generation and document search.
              </p>
              <Link to="/ai-copilot"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-400
                           hover:text-blue-300 transition">
                Launch Copilot
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>

          {/* Quick actions */}
          <div className="lg:col-span-2 bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <h3 className="text-white font-semibold mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {[
                { href:"/production",       label:"New Order",        icon:"M12 4v16m8-8H4",               color:"blue" },
                { href:"/shipments",        label:"Track Shipment",   icon:"M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4", color:"teal" },
                { href:"/inventory",        label:"Check Stock",      icon:"M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8", color:"purple" },
                { href:"/quality",          label:"Log QC Report",    icon:"M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0",  color:"green" },
                { href:"/production-lines", label:"Lines Status",     icon:"M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18", color:"orange" },
                { href:"/knowledge",        label:"Upload Docs",      icon:"M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12", color:"yellow" },
              ].map(({ href, label, icon, color }) => {
                const c = COLOR_MAP[color] || COLOR_MAP.blue;
                return (
                  <Link key={href} to={href}
                    className={`flex items-center gap-2.5 px-3.5 py-3 rounded-xl
                                border ${c.border} ${c.bg} hover:brightness-110 transition group`}>
                    <svg className={`w-4 h-4 ${c.icon} flex-shrink-0`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={icon} />
                    </svg>
                    <span className="text-slate-300 group-hover:text-white text-xs font-medium transition">{label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>

      </div>
    </Layout>
  );
}
