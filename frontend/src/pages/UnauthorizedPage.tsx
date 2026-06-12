import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function UnauthorizedPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full
                        bg-red-500/20 border border-red-500/30 mb-6">
          <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400 mb-2">
          You don't have permission to access this page.
        </p>
        {user && (
          <p className="text-slate-500 text-sm mb-8">
            Your current role is <span className="text-blue-400 font-medium">{user.role}</span>.
            Contact your administrator to request access.
          </p>
        )}

        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="px-5 py-2.5 rounded-xl border border-slate-600 text-slate-300
                       hover:bg-slate-800 transition text-sm font-medium"
          >
            Go Back
          </button>
          <button
            onClick={() => navigate("/dashboard")}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500
                       text-white transition text-sm font-medium"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
