import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { AuthUser } from "../hooks/useAuth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: AuthUser["role"] | AuthUser["role"][];
  minRole?: AuthUser["role"];
}

const ROLE_LEVELS: Record<AuthUser["role"], number> = {
  viewer: 0,
  qc_inspector: 1,
  supervisor: 2,
  manager: 3,
  admin: 4,
};

export default function ProtectedRoute({
  children,
  requiredRole,
  minRole,
}: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();

  // Not logged in → redirect to login, preserve intended URL
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Role check — exact role(s)
  if (requiredRole) {
    const allowed = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!allowed.includes(user.role)) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  // Role check — minimum level
  if (minRole) {
    if (ROLE_LEVELS[user.role] < ROLE_LEVELS[minRole]) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
}
