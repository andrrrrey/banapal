// Хуки мониторинга Битрикс24 (TanStack Query).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";

export interface MonStat {
  n: string;
  label: string;
  cls: string;
}
export interface MonStatsResponse {
  stats: MonStat[];
  badge: number;
}

export interface Violation {
  severity: "over" | "warn" | "review";
  ptype: string;
  kind_label: string;
  kind_class: string;
  name: string;
  ref: string;
  mgr: string;
  src: string;
  norm: string;
  sla: string;
  over: boolean;
  amount: number;
  amount_display: string;
  ai: string;
}

export function useMonitorStats() {
  return useQuery<MonStatsResponse>({
    queryKey: ["monitor", "stats"],
    queryFn: () => api.get("/monitor/stats"),
  });
}

export function useViolations(ptype: string | null) {
  return useQuery<Violation[]>({
    queryKey: ["monitor", "violations", ptype],
    queryFn: () => api.get(`/monitor/violations${ptype ? `?ptype=${encodeURIComponent(ptype)}` : ""}`),
  });
}

export function useReview() {
  return useQuery<Violation[]>({
    queryKey: ["monitor", "review"],
    queryFn: () => api.get("/monitor/review"),
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ref: string) => api.post<{ assignee: string; title: string; due: string }>(
      "/monitor/task",
      { ref },
    ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["monitor"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
