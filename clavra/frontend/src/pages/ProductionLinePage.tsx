import { useEffect, useState, useCallback } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface ActiveOrder {
  id: number; order_no: string; buyer: string; style: string;
  status: string; quantity: number; produced_qty: number; progress_pct: number;
}
interface ProductionLine {
  id: number; line_name: string; supervisor: string; status: string;
  target_output: number; actual_output: number; efficiency: number;
  defects: number; operators: number;
  current_orders: ActiveOrder[];
}
interface OrderOption {
  id: number; order_no: string; buyer: string; style: string; status: string;
}

const LINE_STATUS: Record<string,{bg:string;text:string;dot:string;ring:string}> = {
  "Running":     {bg:"bg-emerald-400/10", text:"text-emerald-400", dot:"bg-emerald-400", ring:"ring-emerald-400/20"},
  "Idle":        {bg:"bg-slate-400/10",   text:"text-slate-400",   dot:"bg-slate-400",   ring:"ring-slate-400/20"  },
  "Maintenance": {bg:"bg-amber-400/10",   text:"text-amber-400",   dot:"bg-amber-400",   ring:"ring-amber-400/20"  },
  "Stopped":     {bg:"bg-red-400/10",     text:"text-red-400",     dot:"bg-red-400",     ring:"ring-red-400/20"    },
};
const ORDER_STAGE: Record<string,{icon:string;color:string}> = {
  "Cutting":   {icon:"✂️",  color:"text-blue-400"},
  "Sewing":    {icon:"🧵",  color:"text-purple-400"},
  "Finishing": {icon:"🪡",  color:"text-teal-400"},
  "Packing":   {icon:"📦", color:"text-amber-400"},
  "Pending":   {icon:"🕒", color:"text-slate-400"},
};
const ALL_STATUSES = ["Running","Idle","Maintenance","Stopped"];

function LineBadge({status}:{status:string}) {
  const m = LINE_STATUS[status] ?? LINE_STATUS["Idle"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border border-current/20 ${m.bg} ${m.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${m.dot}`}/>
      {status}
    </span>
  );
}
function EffBar({pct,h="h-2"}:{pct:number;h?:string}) {
  const color = pct>=90?"bg-emerald-500":pct>=70?"bg-blue-500":pct>=50?"bg-amber-500":"bg-red-500";
  return (
    <div className={`${h} bg-slate-700 rounded-full overflow-hidden`}>
      <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{width:`${Math.min(pct,100)}%`}}/>
    </div>
  );
}

export default function ProductionLinesPage() {
  const [lines,setLines]         = useState<ProductionLine[]>([]);
  const [allOrders,setAllOrders] = useState<OrderOption[]>([]);
  const [loading,setLoading]     = useState(true);
  const [error,setError]         = useState<string|null>(null);
  const [updating,setUpdating]   = useState<number|null>(null);
  const [deletingLine,setDeleting] = useState<number|null>(null);
  const [assignTarget,setAssign] = useState<{lineId:number;lineName:string}|null>(null);
  const [assignOrderId,setAOId]  = useState("");
  const [assigning,setAssigning] = useState(false);
  // Add Line modal
  const [showAddLine,setShowAddLine] = useState(false);
  const [addForm,setAddForm] = useState({line_name:"",supervisor:"",target_output:"",operators:""});
  const [addSaving,setAddSaving]     = useState(false);
  const [addErr,setAddErr]           = useState("");

  const loadLines = useCallback(async () => {
    try {
      setError(null);
      const r = await api.get("/production-lines/");
      setLines(Array.isArray(r.data)?r.data:[]);
    } catch { setError("Failed to load production lines."); }
    finally { setLoading(false); }
  },[]);

  const loadOrders = useCallback(async () => {
    try {
      const r = await api.get("/orders/",{params:{limit:50}});
      const active = (Array.isArray(r.data)?r.data:[]).filter(
        (o:OrderOption)=>!["Completed","Cancelled"].includes(o.status)
      );
      setAllOrders(active);
    } catch {}
  },[]);

  useEffect(()=>{
    loadLines();
    const interval = setInterval(loadLines, 30_000);
    return () => clearInterval(interval);
  },[loadLines]);

  const handleStatusChange = async (id:number,status:string) => {
    setUpdating(id);
    try {
      const r = await api.put(`/production-lines/${id}`,{status});
      setLines(prev=>prev.map(l=>l.id===id?{...l,...r.data}:l));
    } catch { alert("Status update failed."); }
    finally { setUpdating(null); }
  };

  const openAssign = (lineId:number,lineName:string) => {
    loadOrders();
    setAssign({lineId,lineName});
    setAOId("");
  };

  const handleAssign = async () => {
    if (!assignTarget||!assignOrderId) return;
    setAssigning(true);
    try {
      const sel = allOrders.find(o=>String(o.id)===assignOrderId);
      await api.put(`/orders/${assignOrderId}`,{line_id:assignTarget.lineId});
      // Pending orders must start once placed on the floor — auto-promote to Cutting
      if (sel?.status==="Pending") {
        await api.put(`/orders/${assignOrderId}`,{status:"Cutting"});
      }
      await loadLines();
      setAssign(null);
    } catch(e:any) { alert(e?.response?.data?.detail||"Assignment failed."); }
    finally { setAssigning(false); }
  };

  const handleAddLine = async (e:React.FormEvent) => {
    e.preventDefault(); setAddSaving(true); setAddErr("");
    try {
      const r = await api.post("/production-lines/",{
        line_name:     addForm.line_name.trim(),
        supervisor:    addForm.supervisor.trim(),
        target_output: parseInt(addForm.target_output)||0,
        operators:     parseInt(addForm.operators)||0,
      });
      setLines(prev=>[...prev,{...r.data,current_orders:r.data.current_orders??[]}]);
      setShowAddLine(false);
      setAddForm({line_name:"",supervisor:"",target_output:"",operators:""});
    } catch(e:any) { setAddErr(e?.response?.data?.detail||"Failed to create line."); }
    finally { setAddSaving(false); }
  };

  const handleDeleteLine = async (id:number, name:string) => {
    if (!confirm(`Delete "${name}"? All orders assigned to this line will be unassigned.`)) return;
    setDeleting(id);
    try {
      await api.delete(`/production-lines/${id}`);
      setLines(prev => prev.filter(l => l.id !== id));
    } catch(e:any) { alert(e?.response?.data?.detail || "Delete failed."); }
    finally { setDeleting(null); }
  };

  const handleUnassign = async (orderId:number) => {
    try {
      await api.put(`/orders/${orderId}`,{line_id:null});
      await loadLines();
    } catch { alert("Unassign failed."); }
  };

  // Normalise API response — current_orders may be missing on legacy entries
  const safeLines = lines.map(l=>({...l, current_orders: l.current_orders ?? []}));

  // Summary stats
  const running      = safeLines.filter(l=>l.status==="Running").length;
  const avgEff       = safeLines.length ? Math.round(safeLines.reduce((a,l)=>a+l.efficiency,0)/safeLines.length) : 0;
  const totalOps     = safeLines.reduce((a,l)=>a+l.operators,0);
  const activeOrders = safeLines.reduce((a,l)=>a+l.current_orders.length,0);

  return (
    <Layout>
      <div className="p-6 max-w-[1400px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Production Lines</h1>
            <p className="text-sm text-slate-400 mt-0.5">Factory floor real-time monitoring — orders, efficiency, and operator status</p>
          </div>
          <button onClick={()=>{setAddErr("");setShowAddLine(true);}}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-teal-600 to-blue-600
                       hover:brightness-110 text-white text-sm font-semibold rounded-xl transition
                       shadow-lg shadow-teal-900/30">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
            </svg>
            Add Line
          </button>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {l:"Total Lines",     v:lines.length, i:"🏭", c:"text-white"},
            {l:"Running",         v:running,       i:"⚡", c:"text-emerald-400"},
            {l:"Active Orders",   v:activeOrders,  i:"📋", c:"text-blue-400"},
            {l:"Total Operators", v:totalOps,      i:"👷", c:"text-white"},
          ].map(c=>(
            <div key={c.l} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-center gap-4">
              <span className="text-2xl">{c.i}</span>
              <div>
                <p className={`text-2xl font-bold tabular-nums ${c.c}`}>{c.v}</p>
                <p className="text-xs text-slate-400">{c.l}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Avg efficiency banner */}
        {safeLines.length>0&&(
          <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl px-5 py-3 flex items-center gap-4">
            <span className="text-sm text-slate-400 whitespace-nowrap">Overall Floor Efficiency</span>
            <div className="flex-1"><EffBar pct={avgEff} h="h-3"/></div>
            <span className={`text-sm font-bold tabular-nums min-w-[40px] text-right ${avgEff>=90?"text-emerald-400":avgEff>=70?"text-blue-400":avgEff>=50?"text-amber-400":"text-red-400"}`}>{avgEff}%</span>
          </div>
        )}

        {/* Line Performance Comparison */}
        {!loading&&safeLines.length>0&&(
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Line Efficiency Comparison</h3>
              <span className="text-xs text-slate-500 bg-slate-700/50 px-2.5 py-1 rounded-full">
                Best: {Math.max(...safeLines.map(l=>l.efficiency))}% · Avg: {avgEff}%
              </span>
            </div>
            <div className="space-y-3.5">
              {[...safeLines].sort((a,b)=>b.efficiency-a.efficiency).map((line,i)=>{
                const effBg    = line.efficiency>=90?"bg-emerald-500":line.efficiency>=70?"bg-blue-500":line.efficiency>=50?"bg-amber-500":"bg-red-500";
                const effText  = line.efficiency>=90?"text-emerald-400":line.efficiency>=70?"text-blue-400":line.efficiency>=50?"text-amber-400":"text-red-400";
                const outPct   = line.target_output?Math.round(line.actual_output/line.target_output*100):0;
                const rankIcon = i===0?"🥇":i===1?"🥈":"🥉";
                const lm = LINE_STATUS[line.status]??LINE_STATUS["Idle"];
                return (
                  <div key={line.id} className="grid grid-cols-[1.5rem_5rem_1fr_5rem_6rem] sm:grid-cols-[1.5rem_6rem_1fr_5rem_7rem] items-center gap-3">
                    <span className="text-base leading-none">{rankIcon}</span>
                    <div>
                      <p className="text-xs font-semibold text-white truncate">{line.line_name}</p>
                      <span className={`inline-flex items-center gap-1 text-[10px] font-medium ${lm.text}`}>
                        <span className={`w-1 h-1 rounded-full ${lm.dot}`}/>
                        {line.status}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${effBg} transition-all duration-700`} style={{width:`${Math.min(line.efficiency,100)}%`}}/>
                      </div>
                      <div className="h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-slate-500 transition-all duration-700" style={{width:`${Math.min(outPct,100)}%`}}/>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold tabular-nums ${effText}`}>{line.efficiency}%</p>
                      <p className="text-[10px] text-slate-500 tabular-nums">out {outPct}%</p>
                    </div>
                    <div className="text-right hidden sm:block">
                      <p className="text-xs text-slate-300 tabular-nums">{line.actual_output.toLocaleString()} pcs</p>
                      <p className="text-[10px] text-slate-500">of {line.target_output.toLocaleString()}</p>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-3.5 pt-3 border-t border-slate-700/40 flex items-center gap-5 text-[10px] text-slate-600">
              <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-2 rounded bg-slate-400"/>thick bar = efficiency %</span>
              <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-1 rounded bg-slate-500"/>thin bar = output vs target</span>
            </div>
          </div>
        )}

        {error&&<div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 text-sm">{error}</div>}

        {loading ? (
          <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"/></div>
        ) : safeLines.length===0 ? (
          <div className="text-center py-20 text-slate-500">
            <p className="text-4xl mb-3">🏭</p>
            <p className="font-medium">No production lines configured</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
            {safeLines.map(line=>{
              const outputPct = line.target_output ? Math.round(line.actual_output/line.target_output*100) : 0;
              const defectRate = line.actual_output ? Math.round(line.defects/line.actual_output*1000)/10 : 0;
              const m = LINE_STATUS[line.status] ?? LINE_STATUS["Idle"];
              return (
                <div key={line.id} className={`bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden hover:border-slate-600 transition-colors ring-1 ${m.ring}`}>

                  {/* Card header strip */}
                  <div className="px-5 py-4 border-b border-slate-700/40 flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-bold text-white">{line.line_name}</h2>
                      <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                        </svg>
                        {line.supervisor}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <LineBadge status={line.status}/>
                      <button
                        onClick={() => handleDeleteLine(line.id, line.line_name)}
                        disabled={deletingLine === line.id}
                        title="Remove this production line"
                        className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-600
                                   hover:text-red-400 hover:bg-red-500/10 transition disabled:opacity-40">
                        {deletingLine === line.id
                          ? <div className="w-3.5 h-3.5 border border-red-400 border-t-transparent rounded-full animate-spin"/>
                          : <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                            </svg>
                        }
                      </button>
                    </div>
                  </div>

                  {/* ── Current Orders Block ───────────────────────────────── */}
                  <div className="px-5 py-3 border-b border-slate-700/40">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Current Orders</span>
                      <button onClick={()=>openAssign(line.id,line.line_name)}
                        className="text-xs px-2 py-1 rounded-lg border border-teal-600/50 text-teal-400 hover:bg-teal-600/10 transition flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
                        </svg>
                        Assign
                      </button>
                    </div>
                    {line.current_orders.length===0 ? (
                      <div className="text-xs text-slate-500 italic py-2 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-600"/>
                        No order assigned — line is idle
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {line.current_orders.map(o=>{
                          const sm = ORDER_STAGE[o.status] ?? {icon:"⚙️",color:"text-slate-400"};
                          return (
                            <div key={o.id} className="bg-slate-900/50 rounded-xl p-3 space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <span className="font-mono text-sm font-bold text-white">{o.order_no}</span>
                                  <p className="text-xs text-slate-400 mt-0.5">{o.buyer} · <em>{o.style}</em></p>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <span className={`text-xs font-semibold flex items-center gap-1 ${sm.color}`}>
                                    <span>{sm.icon}</span> {o.status}
                                  </span>
                                  <button onClick={()=>handleUnassign(o.id)}
                                    title="Remove from this line"
                                    className="text-slate-600 hover:text-red-400 transition ml-1">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                                    </svg>
                                  </button>
                                </div>
                              </div>
                              {/* progress bar */}
                              <div className="space-y-1">
                                <div className="flex justify-between text-xs">
                                  <span className="text-slate-500">{o.produced_qty.toLocaleString()} / {o.quantity.toLocaleString()} pcs</span>
                                  <span className="text-slate-400 font-medium">{o.progress_pct}%</span>
                                </div>
                                <EffBar pct={o.progress_pct} h="h-1.5"/>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* ── Metrics ──────────────────────────────────────────── */}
                  <div className="px-5 py-3 space-y-3">
                    {/* Efficiency */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Efficiency</span>
                        <span className={`font-bold tabular-nums ${line.efficiency>=90?"text-emerald-400":line.efficiency>=70?"text-blue-400":line.efficiency>=50?"text-amber-400":"text-red-400"}`}>{line.efficiency}%</span>
                      </div>
                      <EffBar pct={line.efficiency}/>
                    </div>
                    {/* Output */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-slate-400">Output</span>
                        <span className="text-slate-300 tabular-nums">{line.actual_output.toLocaleString()} / {line.target_output.toLocaleString()}</span>
                      </div>
                      <EffBar pct={outputPct} h="h-1.5"/>
                    </div>
                    {/* Stats row */}
                    <div className="grid grid-cols-3 gap-2 pt-1">
                      {[{l:"Operators",v:line.operators},{l:"Defects",v:line.defects},{l:"Defect %",v:`${defectRate}%`}].map(s=>(
                        <div key={s.l} className="bg-slate-900/40 rounded-xl p-2 text-center">
                          <p className="text-sm font-bold text-white tabular-nums">{s.v}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{s.l}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* ── Status control ───────────────────────────────────── */}
                  <div className="px-5 py-3 border-t border-slate-700/40 flex items-center justify-between">
                    <span className="text-xs text-slate-500">Change line status</span>
                    <div className="relative">
                      <select value={line.status} onChange={e=>handleStatusChange(line.id,e.target.value)}
                        disabled={updating===line.id}
                        className="appearance-none bg-slate-700/50 border border-slate-600/60 text-slate-300 text-xs rounded-lg pl-3 pr-7 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-500/50 disabled:opacity-40 cursor-pointer hover:bg-slate-700 transition">
                        {ALL_STATUSES.map(s=><option key={s} value={s}>{s}</option>)}
                      </select>
                      {updating===line.id&&(
                        <div className="absolute inset-0 flex items-center justify-center bg-slate-800/80 rounded-lg">
                          <div className="w-3 h-3 border border-teal-400 border-t-transparent rounded-full animate-spin"/>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Line Modal */}
      {showAddLine&&(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-base font-semibold text-white">Add Production Line</h2>
                <p className="text-xs text-slate-500 mt-0.5">New line will start with Running status</p>
              </div>
              <button onClick={()=>setShowAddLine(false)} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <form onSubmit={handleAddLine} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Line Name *</label>
                  <input required value={addForm.line_name}
                    onChange={e=>setAddForm(p=>({...p,line_name:e.target.value}))}
                    placeholder="e.g. Line D, Line E"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"/>
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Supervisor *</label>
                  <input required value={addForm.supervisor}
                    onChange={e=>setAddForm(p=>({...p,supervisor:e.target.value}))}
                    placeholder="Supervisor name"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"/>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Output (pcs/day) *</label>
                  <input required type="number" min="1" value={addForm.target_output}
                    onChange={e=>setAddForm(p=>({...p,target_output:e.target.value}))}
                    placeholder="e.g. 1200"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"/>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Operators *</label>
                  <input required type="number" min="1" value={addForm.operators}
                    onChange={e=>setAddForm(p=>({...p,operators:e.target.value}))}
                    placeholder="e.g. 35"
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50"/>
                </div>
              </div>
              {addErr&&<p className="text-xs text-red-400">{addErr}</p>}
              <div className="flex gap-3 pt-1">
                <button type="button" onClick={()=>setShowAddLine(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">Cancel</button>
                <button type="submit" disabled={addSaving}
                  className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-teal-600 to-blue-600 hover:brightness-110 text-white text-sm font-semibold transition disabled:opacity-50">
                  {addSaving?"Creating…":"Create Line"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Order Modal */}
      {assignTarget&&(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-base font-semibold text-white">Assign Order to Line</h2>
                <p className="text-xs text-slate-500 mt-0.5">{assignTarget.lineName}</p>
              </div>
              <button onClick={()=>setAssign(null)} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Select Production Order</label>
                <select value={assignOrderId} onChange={e=>setAOId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50">
                  <option value="">— Choose an order —</option>
                  {allOrders.map(o=>(
                    <option key={o.id} value={String(o.id)}>
                      {o.order_no}  ·  {o.buyer}  ·  {o.style}  [{o.status}]
                    </option>
                  ))}
                </select>
                {allOrders.length===0&&<p className="text-xs text-slate-500 mt-1.5">No active orders available to assign.</p>}
                {assignOrderId&&allOrders.find(o=>String(o.id)===assignOrderId)?.status==="Pending"&&(
                  <p className="mt-2 text-xs text-amber-400 flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                    <span>⚡</span>
                    <span>This order is <strong>Pending</strong> — placing it on the floor will automatically start it (<strong>Pending → Cutting</strong>).</span>
                  </p>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Order will appear in this line's Current Orders. Pending orders are auto-promoted to Cutting when placed on a line.
              </p>
              <div className="flex gap-3 pt-1">
                <button onClick={()=>setAssign(null)} className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">Cancel</button>
                <button onClick={handleAssign} disabled={!assignOrderId||assigning}
                  className="flex-1 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold transition disabled:opacity-50">
                  {assigning?"Assigning…":"Assign Order"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
