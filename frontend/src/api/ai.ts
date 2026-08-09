// Хук AI-инсайтов (TanStack Query).

import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export interface Insight {
  sev_label: string; sev_class: string; ic: string; icon: string;
  title: string; time: string; surface: string; text: string; rec: string;
  src: string[]; conf: string; dep: boolean;
}

export const useInsights = () =>
  useQuery<Insight[]>({ queryKey: ["ai", "insights"], queryFn: () => api.get("/ai/insights") });
