import { useEffect, useState, useCallback } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";

interface Item {
  id: number; material_code: string; material_name: string; category: string;
  unit: string; stock_qty: number; reserved_qty: number;
  available_qty: number; status: string;
}

const STATUS_META: Record<string,{bg:string;text:string;dot:string}> = {
  "In Stock":     {bg:"bg-emerald-400/10", text:"text-emerald-400", dot:"bg-emerald-400"},
  "Low Stock":    {bg:"bg-amber-400/10",   text:"text-amber-400",   dot:"bg-amber-400"  },
  "Out of Stock": {bg:"bg-red-400/10",     text:"text-red-400",     dot:"bg-red-400"    },
  "Available":    {bg:"bg-emerald-400/10", text:"text-emerald-400", dot:"bg-emerald-400"},
};

function StatusBadge({status}:{status:string}) {
  const m = STATUS_META[status] ?? STATUS_META["In Stock"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border border-current/20 ${m.bg} ${m.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`}/>
      {status}
    </span>
  );
}

function StockBar({item}:{item:Item}) {
  const pct = item.stock_qty > 0 ? Math.round(item.available_qty / item.stock_qty * 100) : 0;
  const color = pct >= 50 ? "bg-emerald-500" : pct >= 20 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{width:`${pct}%`}}/>
      </div>
      <span className="text-xs text-slate-400 tabular-nums w-8 text-right">{pct}%</span>
    </div>
  );
}

const EMPTY_FORM = {material_code:"",material_name:"",category:"",unit:"",stock_qty:""};

export default function InventoryPage() {
  const [items,setItems]         = useState<Item[]>([]);
  const [loading,setLoading]     = useState(true);
  const [error,setError]         = useState("");
  const [search,setSearch]       = useState("");
  const [catFilter,setCatFilter] = useState("");
  const [showAdd,setShowAdd]     = useState(false);
  const [form,setForm]           = useState(EMPTY_FORM);
  const [saving,setSaving]       = useState(false);
  const [editQty,setEditQty]     = useState<{id:number;val:string}|null>(null);
  const [updatingQty,setUpdQty]  = useState<number|null>(null);

  const load = useCallback(async () => {
    try {
      setError("");
      const r = await api.get("/inventory/");
      setItems(Array.isArray(r.data) ? r.data : []);
    } catch(e:any) { setError(e?.response?.data?.detail||"Failed to load inventory."); }
    finally { setLoading(false); }
  },[]);

  useEffect(()=>{ load(); },[load]);

  const createItem = async (e:React.FormEvent) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const r = await api.post("/inventory/",{...form,stock_qty:Number(form.stock_qty)});
      setItems(prev=>[r.data,...prev]);
      setForm(EMPTY_FORM); setShowAdd(false);
    } catch(e:any) { setError(e?.response?.data?.detail||"Failed to add material."); }
    finally { setSaving(false); }
  };

  const updateQty = async (id:number,qty:number) => {
    setUpdQty(id);
    try {
      await api.put(`/inventory/${id}`,{stock_qty:qty});
      setItems(prev=>prev.map(i=>i.id===id?{...i,stock_qty:qty,available_qty:qty-(i.reserved_qty||0)}:i));
      setEditQty(null);
    } catch { alert("Quantity update failed."); }
    finally { setUpdQty(null); }
  };

  const categories = [...new Set(items.map(i=>i.category).filter(Boolean))].sort();
  const filtered = items.filter(i=>{
    const matchSearch = !search||i.material_name.toLowerCase().includes(search.toLowerCase())||i.material_code.toLowerCase().includes(search.toLowerCase());
    const matchCat    = !catFilter||i.category===catFilter;
    return matchSearch&&matchCat;
  });

  const stats = {
    total:    items.length,
    inStock:  items.filter(i=>i.status==="In Stock"||i.status==="Available").length,
    lowStock: items.filter(i=>i.status==="Low Stock").length,
    outStock: items.filter(i=>i.status==="Out of Stock").length,
  };

  const inputCls = "w-full bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50";
  const labelCls = "block text-xs font-medium text-slate-400 mb-1.5";

  return (
    <Layout>
      <div className="p-6 max-w-[1400px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Inventory</h1>
            <p className="text-sm text-slate-400 mt-0.5">Raw material and stock management</p>
          </div>
          <button onClick={()=>setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-teal-900/30">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4"/>
            </svg>
            Add Material
          </button>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {l:"Total Materials", v:stats.total,    i:"📦", cls:"text-white"},
            {l:"In Stock",        v:stats.inStock,  i:"✅", cls:"text-emerald-400"},
            {l:"Low Stock",       v:stats.lowStock, i:"⚠️", cls:"text-amber-400"},
            {l:"Out of Stock",    v:stats.outStock, i:"🚫", cls:"text-red-400"},
          ].map(c=>(
            <div key={c.l} className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-center gap-4">
              <span className="text-2xl">{c.i}</span>
              <div>
                <p className={`text-2xl font-bold tabular-nums ${c.cls}`}>{c.v}</p>
                <p className="text-xs text-slate-400">{c.l}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Alert banner for low/out-of-stock */}
        {(stats.lowStock>0||stats.outStock>0)&&(
          <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-xl px-4 py-3 text-sm">
            <span className="text-lg">⚠️</span>
            <span>
              {stats.outStock>0&&<strong>{stats.outStock} item{stats.outStock>1?"s":""} out of stock</strong>}
              {stats.outStock>0&&stats.lowStock>0&&" · "}
              {stats.lowStock>0&&<span>{stats.lowStock} item{stats.lowStock>1?"s":""} running low</span>}
              {" — consider restocking soon."}
            </span>
          </div>
        )}

        {error&&<div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-4 text-sm">{error}</div>}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input value={search} onChange={e=>setSearch(e.target.value)}
              placeholder="Search by code or name…"
              className="bg-slate-800 border border-slate-700 text-white pl-9 pr-4 py-2 text-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/50 w-64"/>
          </div>
          {categories.length>0&&(
            <select value={catFilter} onChange={e=>setCatFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500/50">
              <option value="">All Categories</option>
              {categories.map(c=><option key={c} value={c}>{c}</option>)}
            </select>
          )}
          <span className="text-slate-500 text-sm ml-auto">{filtered.length} item{filtered.length!==1?"s":""}</span>
          <span className="text-xs text-slate-600">Click <span className="text-teal-400 font-medium">stock qty</span> to update inline</span>
        </div>

        {/* Table */}
        {loading ? (
          <div className="flex justify-center py-20"><div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin"/></div>
        ) : filtered.length===0 ? (
          <div className="text-center py-20 text-slate-500">
            <p className="text-4xl mb-3">📦</p>
            <p className="font-medium">{search||catFilter?"No materials match your filter.":"No materials yet."}</p>
            {!search&&!catFilter&&<p className="text-sm mt-1">Add your first material using the button above.</p>}
          </div>
        ) : (
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50 bg-slate-900/40">
                    {["Code","Material Name","Category","Unit","Stock Qty","Reserved","Available","Level","Status"].map(h=>(
                      <th key={h} className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wide px-4 py-3.5 first:pl-5 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/30">
                  {filtered.map(it=>(
                    <tr key={it.id} className="hover:bg-slate-700/20 transition-colors">
                      <td className="px-5 py-4"><span className="font-mono text-xs text-blue-300 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded">{it.material_code}</span></td>
                      <td className="px-4 py-4"><span className="font-medium text-slate-200">{it.material_name}</span></td>
                      <td className="px-4 py-4"><span className="text-xs text-slate-400 bg-slate-700/50 px-2 py-0.5 rounded-md">{it.category||"—"}</span></td>
                      <td className="px-4 py-4 text-slate-400 text-xs">{it.unit}</td>
                      <td className="px-4 py-4">
                        {editQty?.id===it.id ? (
                          <div className="flex items-center gap-1.5">
                            <input type="number" min={0} value={editQty.val}
                              onChange={e=>setEditQty({id:it.id,val:e.target.value})}
                              onKeyDown={e=>{if(e.key==="Enter")updateQty(it.id,Number(editQty.val));if(e.key==="Escape")setEditQty(null);}}
                              autoFocus
                              className="w-20 bg-slate-900 border border-teal-500/50 text-white text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-500/50"/>
                            <button onClick={()=>updateQty(it.id,Number(editQty.val))} disabled={updatingQty===it.id}
                              className="text-xs px-2 py-1.5 bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition disabled:opacity-50">
                              {updatingQty===it.id?"…":"✓"}
                            </button>
                            <button onClick={()=>setEditQty(null)} className="text-xs px-1.5 py-1.5 text-slate-400 hover:text-white transition">✕</button>
                          </div>
                        ) : (
                          <button onClick={()=>setEditQty({id:it.id,val:String(it.stock_qty)})}
                            className="group flex items-center gap-1.5 text-slate-300 font-mono hover:text-teal-300 transition">
                            {it.stock_qty.toLocaleString()}
                            <svg className="w-3 h-3 text-slate-600 group-hover:text-teal-400 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                            </svg>
                          </button>
                        )}
                      </td>
                      <td className="px-4 py-4 text-slate-400 font-mono text-xs">{it.reserved_qty?.toLocaleString()??0}</td>
                      <td className="px-4 py-4 font-mono font-semibold text-slate-200 text-sm">{it.available_qty?.toLocaleString()}</td>
                      <td className="px-4 py-4"><StockBar item={it}/></td>
                      <td className="px-4 py-4"><StatusBadge status={it.status}/></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Add Material Modal */}
      {showAdd&&(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-base font-semibold text-white">Add Material</h2>
              <button onClick={()=>{setShowAdd(false);setForm(EMPTY_FORM);setError("");}} className="text-slate-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <form onSubmit={createItem} className="p-6 space-y-4">
              {error&&<div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-3 text-xs">{error}</div>}
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Material Code *</label><input value={form.material_code} onChange={e=>setForm(f=>({...f,material_code:e.target.value}))} placeholder="e.g. FAB-001" required className={inputCls}/></div>
                <div><label className={labelCls}>Material Name *</label><input value={form.material_name} onChange={e=>setForm(f=>({...f,material_name:e.target.value}))} placeholder="e.g. Cotton Fabric" required className={inputCls}/></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className={labelCls}>Category</label><input value={form.category} onChange={e=>setForm(f=>({...f,category:e.target.value}))} placeholder="e.g. Fabric, Thread, Button" className={inputCls}/></div>
                <div><label className={labelCls}>Unit</label><input value={form.unit} onChange={e=>setForm(f=>({...f,unit:e.target.value}))} placeholder="e.g. Roll, KG, Piece" className={inputCls}/></div>
              </div>
              <div><label className={labelCls}>Opening Stock Quantity *</label><input type="number" min={0} value={form.stock_qty} onChange={e=>setForm(f=>({...f,stock_qty:e.target.value}))} placeholder="0" required className={inputCls}/></div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={()=>{setShowAdd(false);setForm(EMPTY_FORM);setError("");}} className="flex-1 py-2.5 rounded-xl border border-slate-600 text-slate-300 hover:bg-slate-700 transition text-sm font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-sm font-semibold transition disabled:opacity-50">{saving?"Adding…":"Add Material"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
