import { useState, useEffect, useCallback } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface Shipment {
  id: number; shipment_no: string; buyer: string | null; destination: string | null;
  carrier: string | null; status: string; eta: string | null;
  actual_departure: string | null; order_id: number | null;
  order_no: string | null; order_style: string | null; created_at: string | null;
}
interface OrderOption {
  id: number; order_no: string; buyer: string; style: string;
  delivery_date: string | null; already_linked: boolean;
}

const STATUSES = ["Pending","In Transit","Customs","Delivered","Delayed","Cancelled"];
const STATUS_META: Record<string,{dot:string;bg:string;text:string}> = {
  "Pending":      {dot:"bg-slate-400",   bg:"bg-slate-400/10",   text:"text-slate-400"  },
  "In Transit":   {dot:"bg-blue-400",    bg:"bg-blue-400/10",    text:"text-blue-400"   },
  "Customs":      {dot:"bg-amber-400",   bg:"bg-amber-400/10",   text:"text-amber-400"  },
  "Delivered":    {dot:"bg-emerald-400", bg:"bg-emerald-400/10", text:"text-emerald-400"},
  "Delayed":      {dot:"bg-orange-400",  bg:"bg-orange-400/10",  text:"text-orange-400" },
  "Cancelled":    {dot:"bg-red-400",     bg:"bg-red-400/10",     text:"text-red-400"    },
};
const PIPELINE = ["Pending","In Transit","Customs","Delivered"];

function StatusBadge({status}:{status:string}) {
  const m = STATUS_META[status] ?? {dot:"bg-slate-400",bg:"bg-slate-400/10",text:"text-slate-300"};
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-current/20 ${m.bg} ${m.text}`}>
    <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`}/>{status}
  </span>;
}
function StatusPipeline({status}:{status:string}) {
  if (status==="Cancelled") return <span className="text-xs text-red-400 font-medium">Cancelled</span>;
  const cur = PIPELINE.indexOf(status);
  return <div className="flex items-center gap-1">
    {PIPELINE.map((step,i)=>(
      <div key={step} className="flex items-center gap-1">
        <div title={step} className={`w-2 h-2 rounded-full transition-all ${i<cur?"bg-emerald-500":i===cur?"bg-blue-400 ring-2 ring-blue-400/30":"bg-slate-700"}`}/>
        {i<PIPELINE.length-1 && <div className={`w-4 h-px ${i<cur?"bg-emerald-500/60":"bg-slate-700"}`}/>}
      </div>
    ))}
    <span className="text-xs text-slate-400 ml-1 whitespace-nowrap">{status}</span>
  </div>;
}
function DateCell({date}:{date:string|null}) {
  if (!date) return <span className="text-slate-600 text-xs">—</span>;
  return <span className="text-xs text-slate-300 font-medium">{new Date(date).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})}</span>;
}
function EtaCell({eta,status}:{eta:string|null;status:string}) {
  if (!eta) return <span className="text-slate-600 text-xs">—</span>;
  const d=new Date(eta), t=new Date(), done=status==="Delivered"||status==="Cancelled";
  const over=!done&&d<t, soon=!done&&!over&&(d.getTime()-t.getTime())<3*86400_000;
  return <span className={`text-xs font-medium flex items-center gap-1 ${over?"text-red-400":soon?"text-amber-400":"text-slate-300"}`}>
    {over&&<span title="Overdue">⚠</span>}{soon&&!over&&<span>🔔</span>}
    {d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})}
  </span>;
}

const EMPTY_EDIT = {order_id:"",carrier:"",actual_departure:"",eta:"",destination:""};

export default function ShipmentPage() {
  const [shipments,setShipments]   = useState<Shipment[]>([]);
  const [orders,setOrders]         = useState<OrderOption[]>([]);
  const [loading,setLoading]       = useState(true);
  const [error,setError]           = useState<string|null>(null);
  const [statusFilter,setFilter]   = useState("");
  const [showBook,setShowBook]     = useState(false);
  const [editTarget,setEditTarget] = useState<Shipment|null>(null);
  const [editForm,setEditForm]     = useState(EMPTY_EDIT);
  const [updating,setUpdating]     = useState<number|null>(null);
  const [saving,setSaving]         = useState(false);
  const [bookForm,setBookForm]     = useState({shipment_no:"",order_id:"",buyer:"",destination:"",carrier:"",actual_departure:"",eta:""});

  const fetchShipments = useCallback(async () => {
    try {
      setError(null);
      const p: Record<string,string> = {};
      if (statusFilter) p.status = statusFilter;
      const r = await api.get("/shipments/",{params:p});
      setShipments(r.data);
    } catch { setError("Failed to load shipments."); }
    finally  { setLoading(false); }
  },[statusFilter]);

  const fetchOrders = useCallback(async () => {
    try { const r = await api.get("/shipments/unlinked-orders"); setOrders(r.data); }
    catch {}
  },[]);

  useEffect(()=>{ fetchShipments(); },[fetchShipments]);

  const handleOrderSelect = (orderId:string, setter:(fn:(f:any)=>any)=>void) => {
    const sel = orders.find(o=>String(o.id)===orderId);
    setter(f=>({...f,order_id:orderId,buyer:sel?.buyer??f.buyer,
      shipment_no:f.shipment_no||(sel?`SHP-${sel.order_no.replace(/\D/g,"")}`:""),
    }));
  };

  const handleBook = async (e:React.FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      const p: Record<string,unknown> = {
        shipment_no:bookForm.shipment_no, buyer:bookForm.buyer||undefined,
        destination:bookForm.destination||undefined, carrier:bookForm.carrier||undefined,
        order_id:bookForm.order_id?parseInt(bookForm.order_id):undefined,
      };
      if (bookForm.actual_departure) p.actual_departure=new Date(bookForm.actual_departure).toISOString();
      if (bookForm.eta)              p.eta=new Date(bookForm.eta).toISOString();
      const r = await api.post("/shipments/",p);
      setShipments(prev=>[r.data,...prev]);
      setShowBook(false);
      setBookForm({shipment_no:"",order_id:"",buyer:"",destination:"",carrier:"",actual_departure:"",eta:""});
      fetchOrders();
    } catch(err:any) { alert(err.response?.data?.detail||"Failed to book shipment."); }
    finally { setSaving(false); }
  };

  const openEdit = (s:Shipment) => {
    fetchOrders();
    setEditTarget(s);
    setEditForm({
      order_id:    s.order_id?String(s.order_id):"",
      carrier:     s.carrier??"",
      actual_departure: s.actual_departure?s.actual_departure.slice(0,10):"",
      eta:         s.eta?s.eta.slice(0,10):"",
      destination: s.destination??"",
    });
  };

  const handleSave = async (e:React.FormEvent) => {
    e.preventDefault(); if (!editTarget) return; setSaving(true);
    try {
      const p: Record<string,unknown> = {
        carrier:     editForm.carrier||undefined,
        destination: editForm.destination||undefined,
        order_id:    editForm.order_id?parseInt(editForm.order_id):null,
      };
      if (editForm.actual_departure) p.actual_departure=new Date(editForm.actual_departure).toISOString();
      if (editForm.eta)              p.eta=new Date(editForm.eta).toISOString();
      const r = await api.put(`/shipments/${editTarget.id}`,p);
      setShipments(prev=>prev.map(s=>s.id===editTarget.id?r.data:s));
      setEditTarget(null);
      fetchOrders();
    } catch(err:any) { alert(err.response?.data?.detail||"Update failed."); }
    finally { setSaving(false); }
  };

  const handleStatusChange = async (id:number,status:string) => {
    setUpdating(id);
    try {
      await api.put(`/shipments/${id}`,{status});
      setShipments(prev=>prev.map(s=>s.id===id?{...s,status}:s));
    } catch { alert("Status update failed."); }
    finally { setUpdating(null); }
  };

  const stats = {
    total:     shipments.length,
    inTransit: shipments.filter(s=>s.status==="In Transit").length,
    delivered: shipments.filter(s=>s.status==="Delivered").length,
    linked:    shipments.filter(s=>!!s.order_no).length,
  };

  const inputCls = "w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50";
  const labelCls = "block text-xs font-medium text-slate-400 mb-1.5";

  return (
    <Layout>
      <div className="p-6 max-w-[1400px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Shipments</h1>
            <p className="text-sm text-slate-400 mt-0.5">Track outbound shipments linked to production orders</p>
          </div>
          <button onClick={()=>{fetchOrders();setShowBook(true);}}
            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-teal-900/30">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
            </svg>
            Book Shipment
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[{l:"Total Shipments",v:stats.total,i:"🚢"},{l:"In Transit",v:stats.inTransit,i:"✈️"},{l:"Delivered",v:stats.delivered,i:"✅"},{l:"Order Linked",v:stats.linked,i:"🔗"}].map(c=>(
            <div key={c.l} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-center gap-4">
              <span className="text-2xl">{c.i}</span>
              <div><p className="text-2xl font-bold text-white tabular-nums">{c.v}</p><p className="text-xs text-slate-400">{c.l}</p></div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select value={statusFilter} onChange={e=>{setFilter(e.target.value);setLoading(true);}}
            className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500/50">
            <option value="">All Statuses</option>
            {STATUSES.map(s=><option key={s} value={s}>{s}</option>)}
          </select>
          <span className="text-slate-500 text-sm">{shipments.length} shipment{shipments.length!==1?"s":""}</span>
          <span className="text-xs text-slate-600 ml-auto">Click <span className="text-teal-400 font-medium">Edit</span> to link an order or update dates</span>
        </div>

        {/* Table */}
        {error ? (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 text-sm">{error}</div>
        ) : loading ? (
          <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"/></div>
        ) : shipments.length===0 ? (
          <div className="text-center py-20 text-slate-500">
            <p className="text-4xl mb-3">🚢</p><p className="font-medium">No shipments yet</p>
            <p className="text-sm mt-1">Book your first shipment and link it to a production order.</p>
          </div>
        ) : (
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 bg-slate-900/40">
                    {["Shipment No","Linked Order","Buyer / Destination","Carrier","Ship Date","ETA","Pipeline","Status","Update",""].map(h=>(
                      <th key={h} className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3.5 first:pl-5 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/30">
                  {shipments.map(s=>(
                    <tr key={s.id} className="hover:bg-slate-700/20 transition-colors">
                      <td className="px-5 py-4"><span className="font-mono font-semibold text-white">{s.shipment_no}</span></td>
                      <td className="px-4 py-4">
                        {s.order_no ? (
                          <div className="space-y-1">
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-bold text-white bg-blue-600/80 border border-blue-400/40 shadow-sm shadow-blue-900/40">
                              🔗 {s.order_no}
                            </span>
                            {s.order_style&&<p className="text-xs text-slate-400 font-medium">{s.order_style}</p>}
                          </div>
                        ) : (
                          <button onClick={()=>openEdit(s)} className="text-xs text-amber-400 hover:text-amber-300 transition flex items-center gap-1 border border-amber-500/30 rounded-lg px-2 py-1 hover:bg-amber-500/10">
                            <span>⚠</span> Link order
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-4"><p className="font-medium text-slate-200">{s.buyer??"—"}</p><p className="text-xs text-slate-500 mt-0.5">{s.destination??"—"}</p></td>
                      <td className="px-4 py-4"><span className="text-sm text-slate-300">{s.carrier??<span className="text-slate-600">—</span>}</span></td>
                      <td className="px-4 py-4"><DateCell date={s.actual_departure}/></td>
                      <td className="px-4 py-4"><EtaCell eta={s.eta} status={s.status}/></td>
                      <td className="px-4 py-4"><StatusPipeline status={s.status}/></td>
                      <td className="px-4 py-4"><StatusBadge status={s.status}/></td>
                      <td className="px-4 py-4">
                        <div className="relative inline-block">
                          <select value={s.status} onChange={e=>handleStatusChange(s.id,e.target.value)}
                            disabled={updating===s.id||s.status==="Cancelled"}
                            className="appearance-none bg-slate-700/50 border border-slate-600/60 text-slate-300 text-xs rounded-lg pl-3 pr-7 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-500/50 disabled:opacity-40 cursor-pointer hover:bg-slate-700 transition">
                            {STATUSES.map(st=><option key={st} value={st}>{st}</option>)}
                          </select>
                          {updating===s.id&&<div className="absolute inset-0 flex items-center justify-center bg-slate-800/80 rounded-lg"><div className="w-3 h-3 border border-teal-400 border-t-transparent rounded-full animate-spin"/></div>}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <button onClick={()=>openEdit(s)}
                          className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white transition flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                          </svg>
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Book Shipment Modal */}
      {showBook&&(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 sticky top-0 bg-slate-900 z-10">
              <h2 className="text-base font-semibold text-white">Book New Shipment</h2>
              <button onClick={()=>setShowBook(false)} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <form onSubmit={handleBook} className="p-6 space-y-4">
              <div>
                <label className={labelCls}>Link to Production Order <span className="text-slate-500 font-normal">(recommended)</span></label>
                <select value={bookForm.order_id} onChange={e=>handleOrderSelect(e.target.value,setBookForm as any)}
                  className={inputCls+" text-slate-300"}>
                  <option value="">— Select an order —</option>
                  {orders.map(o=><option key={o.id} value={String(o.id)}>{o.order_no}  ·  {o.buyer}  ·  {o.style}{o.already_linked?"  [has shipment]":""}</option>)}
                </select>
                {bookForm.order_id&&(()=>{const sel=orders.find(o=>String(o.id)===bookForm.order_id);return sel?.delivery_date?<p className="text-xs text-teal-400 mt-1.5">📅 Order delivery: {new Date(sel.delivery_date).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})} — align ETA to this.</p>:null;})()}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Shipment No *</label><input value={bookForm.shipment_no} onChange={e=>setBookForm(f=>({...f,shipment_no:e.target.value}))} placeholder="e.g. SHP-004" required className={inputCls}/></div>
                <div><label className={labelCls}>Buyer</label><input value={bookForm.buyer} onChange={e=>setBookForm(f=>({...f,buyer:e.target.value}))} placeholder="Auto-filled from order" className={inputCls}/></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Destination</label><input value={bookForm.destination} onChange={e=>setBookForm(f=>({...f,destination:e.target.value}))} placeholder="e.g. Hamburg, Germany" className={inputCls}/></div>
                <div><label className={labelCls}>Carrier</label><input value={bookForm.carrier} onChange={e=>setBookForm(f=>({...f,carrier:e.target.value}))} placeholder="e.g. Maersk Line" className={inputCls}/></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Ship Date</label><input type="date" value={bookForm.actual_departure} onChange={e=>setBookForm(f=>({...f,actual_departure:e.target.value}))} className={inputCls+" text-slate-300"}/></div>
                <div><label className={labelCls}>ETA</label><input type="date" value={bookForm.eta} onChange={e=>setBookForm(f=>({...f,eta:e.target.value}))} className={inputCls+" text-slate-300"}/></div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={()=>setShowBook(false)} className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold transition disabled:opacity-50">{saving?"Booking…":"Book Shipment"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit / Link Modal */}
      {editTarget&&(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <div>
                <h2 className="text-base font-semibold text-white">Edit Shipment</h2>
                <p className="text-xs text-slate-500 mt-0.5 font-mono">{editTarget.shipment_no}</p>
              </div>
              <button onClick={()=>setEditTarget(null)} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4">
              <div>
                <label className={labelCls}>Link to Production Order</label>
                <select value={editForm.order_id} onChange={e=>setEditForm(f=>({...f,order_id:e.target.value}))}
                  className={inputCls+" text-slate-300"}>
                  <option value="">— No order linked —</option>
                  {orders.map(o=><option key={o.id} value={String(o.id)}>{o.order_no}  ·  {o.buyer}  ·  {o.style}{o.already_linked&&String(o.id)!==editForm.order_id?"  [linked to other]":""}</option>)}
                </select>
                {editTarget.order_no&&!editForm.order_id&&<p className="text-xs text-amber-400 mt-1">Currently linked to <strong>{editTarget.order_no}</strong>. Set a new order above to change it.</p>}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Destination</label><input value={editForm.destination} onChange={e=>setEditForm(f=>({...f,destination:e.target.value}))} placeholder="e.g. Hamburg, Germany" className={inputCls}/></div>
                <div><label className={labelCls}>Carrier</label><input value={editForm.carrier} onChange={e=>setEditForm(f=>({...f,carrier:e.target.value}))} placeholder="e.g. Maersk Line" className={inputCls}/></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Ship Date <span className="text-slate-500 font-normal">(departure)</span></label><input type="date" value={editForm.actual_departure} onChange={e=>setEditForm(f=>({...f,actual_departure:e.target.value}))} className={inputCls+" text-slate-300"}/></div>
                <div><label className={labelCls}>ETA at Destination</label><input type="date" value={editForm.eta} onChange={e=>setEditForm(f=>({...f,eta:e.target.value}))} className={inputCls+" text-slate-300"}/></div>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={()=>setEditTarget(null)} className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold transition disabled:opacity-50">{saving?"Saving…":"Save Changes"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
