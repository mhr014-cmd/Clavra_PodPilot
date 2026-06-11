// Legacy auth service — superseded by useAuth hook
// Kept for any remaining references
import api from "../api/axios";

export async function loginUser(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}

export async function registerUser(data: {
  full_name: string; email: string; password: string; role?: string;
}) {
  const res = await api.post("/auth/register", data);
  return res.data;
}
