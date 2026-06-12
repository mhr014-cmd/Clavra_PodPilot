import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  minRole?: string;
}

const Icon = ({ d }: { d: string }) => (
  <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={d} />
  </svg>
);

const NAV: NavItem[] = [
  { path: "/dashboard",        label: "Dashboard",        icon: <Icon d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/> },
  { path: "/production",       label: "Production",       icon: <Icon d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/> },
  { path: "/production-lines", label: "Production Lines", icon: <Icon d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/> },
  { path: "/shipments",        label: "Shipments",        icon: <Icon d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/> },
  { path: "/inventory",        label: "Inventory",        icon: <Icon d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/> },
  { path: "/quality",          label: "Quality",          icon: <Icon d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"/> },
  { path: "/ai-copilot",       label: "AI Copilot",       icon: <Icon d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>, minRole: "supervisor" },
  { path: "/knowledge",        label: "Knowledge Base",   icon: <Icon d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>, minRole: "supervisor" },
];

const ROLE_LEVELS: Record<string, number> = {
  viewer: 0, qc_inspector: 1, supervisor: 2, manager: 3, admin: 4
};

export default function Sidebar() {
  const navigate    = useNavigate();
  const { user, logout } = useAuth();

  const canAccess = (minRole?: string) => {
    if (!minRole || !user) return true;
    return (ROLE_LEVELS[user.role] || 0) >= (ROLE_LEVELS[minRole] || 0);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="w-56 bg-slate-950 min-h-screen flex flex-col border-r border-slate-800/60 flex-shrink-0">

      {/* Brand */}
      <div className="px-4 py-4 border-b border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-teal-500
                          flex items-center justify-center flex-shrink-0
                          shadow-lg shadow-blue-500/30">
            <span className="text-white text-xs font-black tracking-tight">CP</span>
          </div>
          <div>
            <p className="text-white font-bold text-sm leading-tight">ProdPilot™</p>
            <p className="text-slate-500 text-xs">Clavra Manufacturing AI</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV.filter(item => canAccess(item.minRole)).map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150
               ${isActive
                 ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md shadow-blue-500/20"
                 : "text-slate-400 hover:text-white hover:bg-slate-800/70"}`
            }
          >
            {item.icon}
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User + Logout */}
      <div className="px-2 py-3 border-t border-slate-800/60 space-y-1">
        {user && (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-slate-900/50">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-700 to-teal-700
                            flex items-center justify-center flex-shrink-0 shadow">
              <span className="text-white text-xs font-bold">
                {user.full_name?.charAt(0)?.toUpperCase() || "U"}
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-slate-200 text-xs font-medium truncate">{user.full_name}</p>
              <p className="text-slate-500 text-xs capitalize">{user.role.replace("_", " ")}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm
                     text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="font-medium">Sign out</span>
        </button>
      </div>
    </div>
  );
}
