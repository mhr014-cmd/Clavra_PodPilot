import { useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":        "Dashboard",
  "/production":       "Production",
  "/production-lines": "Production Lines",
  "/shipments":        "Shipments",
  "/inventory":        "Inventory",
  "/quality":          "Quality Control",
  "/ai-copilot":       "AI Copilot",
  "/knowledge":        "Knowledge Base",
};

const ROLE_BADGE: Record<string, string> = {
  admin:        "bg-red-500/20 text-red-400",
  manager:      "bg-orange-500/20 text-orange-400",
  supervisor:   "bg-yellow-500/20 text-yellow-400",
  qc_inspector: "bg-teal-500/20 text-teal-400",
  viewer:       "bg-slate-500/20 text-slate-400",
};

export default function Navbar() {
  const { user } = useAuth();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || "Clavra ProdPilot™";

  return (
    <div className="h-16 bg-slate-900 border-b border-slate-800/50
                    flex items-center justify-between px-6 flex-shrink-0">
      {/* Page title */}
      <div>
        <h1 className="text-white font-semibold text-lg leading-tight">{title}</h1>
        <p className="text-slate-500 text-xs">Clavra ProdPilot™ Manufacturing OS</p>
      </div>

      {/* Right: role badge + avatar */}
      {user && (
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium capitalize
                            ${ROLE_BADGE[user.role] || ROLE_BADGE.viewer}`}>
            {user.role.replace("_", " ")}
          </span>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-teal-600
                            flex items-center justify-center shadow-sm">
              <span className="text-white text-xs font-bold">
                {user.full_name?.charAt(0)?.toUpperCase() || "U"}
              </span>
            </div>
            <div className="hidden sm:block">
              <p className="text-white text-xs font-medium leading-tight">{user.full_name}</p>
              <p className="text-slate-500 text-xs">{user.email}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
