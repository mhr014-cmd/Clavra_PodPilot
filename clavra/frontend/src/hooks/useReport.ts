import { useState } from "react";
import api from "../api/axios";

export type ReportType =
  | "orders"
  | "shipments"
  | "inventory"
  | "quality"
  | "production-lines"
  | "summary";

export interface ReportFilters {
  status?: string;
  buyer?: string;
  from_date?: string;
  to_date?: string;
  severity?: string;
  category?: string;
}

export function useReport() {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const download = async (type: ReportType, filters: ReportFilters = {}) => {
    setLoading(true);
    setError(null);
    try {
      // Strip empty string params
      const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v && v.trim() !== "")
      );
      const res = await api.get(`/reports/${type}`, {
        params,
        responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `clavra_${type}_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to generate report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return { download, loading, error };
}
