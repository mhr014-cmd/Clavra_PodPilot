import { create } from "zustand";
import { persist } from "zustand/middleware";
import api from "../api/axios";

// ── Types ─────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  role: "admin" | "manager" | "supervisor" | "qc_inspector" | "viewer";
  org_id: number | null;
  is_active: boolean;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
  fetchMe: () => Promise<void>;
  setTokens: (accessToken: string, user: AuthUser) => void;
  clearAuth: () => void;
  hasRole: (...roles: AuthUser["role"][]) => boolean;
  hasMinRole: (minRole: AuthUser["role"]) => boolean;
}

// ── Role hierarchy ────────────────────────────────────────────────────────

const ROLE_LEVELS: Record<AuthUser["role"], number> = {
  viewer: 0,
  qc_inspector: 1,
  supervisor: 2,
  manager: 3,
  admin: 4,
};

// ── Store ─────────────────────────────────────────────────────────────────

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // ── Login ──────────────────────────────────────────────────────────
      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const res = await api.post("/auth/login", { email, password });
          const { access_token, user } = res.data;
          set({
            accessToken: access_token,
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          // Store for axios interceptor
          localStorage.setItem("clavra_access_token", access_token);
        } catch (err: any) {
          const msg = err?.response?.data?.detail || "Login failed";
          set({ isLoading: false, error: msg, isAuthenticated: false });
          throw new Error(msg);
        }
      },

      // ── Logout ─────────────────────────────────────────────────────────
      logout: async () => {
        try {
          await api.post("/auth/logout");
        } catch {
          // Proceed regardless
        } finally {
          get().clearAuth();
        }
      },

      // ── Refresh token ──────────────────────────────────────────────────
      refreshToken: async () => {
        try {
          const res = await api.post("/auth/refresh");
          const { access_token } = res.data;
          set({ accessToken: access_token });
          localStorage.setItem("clavra_access_token", access_token);
          return access_token;
        } catch {
          get().clearAuth();
          return null;
        }
      },

      // ── Fetch current user ─────────────────────────────────────────────
      fetchMe: async () => {
        try {
          const res = await api.get("/auth/me");
          set({ user: res.data, isAuthenticated: true });
        } catch {
          get().clearAuth();
        }
      },

      // ── Setters ────────────────────────────────────────────────────────
      setTokens: (accessToken, user) => {
        localStorage.setItem("clavra_access_token", accessToken);
        set({ accessToken, user, isAuthenticated: true });
      },

      clearAuth: () => {
        localStorage.removeItem("clavra_access_token");
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      // ── Role helpers ───────────────────────────────────────────────────
      hasRole: (...roles) => {
        const { user } = get();
        if (!user) return false;
        return roles.includes(user.role);
      },

      hasMinRole: (minRole) => {
        const { user } = get();
        if (!user) return false;
        return ROLE_LEVELS[user.role] >= ROLE_LEVELS[minRole];
      },
    }),
    {
      name: "clavra_auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
