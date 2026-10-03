import { useQuery } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";

export interface Company {
  id: number;
  name: string;
  description?: string | null;
  status?: string;
  frequency_hours?: number;
  next_run_time?: string | null;
  is_processing: boolean;
  pending_ideas_count: number | null;
  created_at?: string;
}

export function useCompanies() {
  return useQuery<Company[]>({
    queryKey: ["companies"],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/companies/`);
      if (!res.ok) {
        throw new Error(`Failed to fetch companies: ${res.statusText}`);
      }
      return res.json();
    },
    refetchInterval: 5000,
  });
}

export function useCompany(id: string | number) {
  return useQuery<Company>({
    queryKey: ["company", String(id)],
    queryFn: async () => {
      const res = await fetch(`${API_URL}/companies/${id}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch company: ${res.statusText}`);
      }
      return res.json();
    },
    enabled: !!id,
    refetchInterval: 10000,
  });
}
