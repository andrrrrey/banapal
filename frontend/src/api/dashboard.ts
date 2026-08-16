// Хуки дашборда (TanStack Query).

import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export interface Kpi {
  key: string;
  label: string;
  icon: string;
  svg: string;
  kind: string;
  value: number | null;
  display: string;
  trend: "up" | "down" | "warn";
  delta: string;
  spark: number[];
  drill: string | null;
  period_label: string;
}

export interface AttentionTile {
  n: number;
  label: string;
  sub: string;
  cls: string;
  icon: string;
  drill: string;
}
export interface Attention {
  money_at_risk: number;
  money_at_risk_display: string;
  risk_leads: number;
  tiles: AttentionTile[];
}

export interface FunnelStage { label: string; value: number; }
export interface Source { name: string; short_name: string; color: string; leads: number; }
export interface RevenueSeries { days: string[]; revenue: number[]; margin: number[]; }
export interface RomiByChannel { name: string; short_name: string; romi: number; }

export interface Manager {
  name: string; inwork: number; overdue: number; notask: number; fc: string;
  invoices: number; payments: number; paysum: number; paysum_display: string;
  zone_label: string; zone_class: string;
}

export interface Lead {
  name: string; src: string; mgr: string; status_label: string; status_class: string;
  fc: string; call: boolean; inv: boolean; pay: boolean; amount: number; amount_display: string;
  risk: string | null; tags: string[]; ai: string; reason: string;
}

const P = (period: string) => `?period=${encodeURIComponent(period)}`;

export interface FilterOptions { managers: string[]; channels: string[]; sources: string[]; }

export const useFilterOptions = () =>
  useQuery<FilterOptions>({
    queryKey: ["dashboard", "filters"],
    queryFn: () => api.get("/dashboard/filters"),
    staleTime: 60_000,
  });

export const useKpis = (period: string) =>
  useQuery<Kpi[]>({ queryKey: ["dashboard", "kpis", period], queryFn: () => api.get(`/dashboard/kpis${P(period)}`) });

export const useAttention = () =>
  useQuery<Attention>({ queryKey: ["dashboard", "attention"], queryFn: () => api.get("/dashboard/attention") });

export const useFunnel = (period: string) =>
  useQuery<FunnelStage[]>({ queryKey: ["dashboard", "funnel", period], queryFn: () => api.get(`/dashboard/funnel${P(period)}`) });

export const useSources = () =>
  useQuery<Source[]>({ queryKey: ["dashboard", "sources"], queryFn: () => api.get("/dashboard/sources") });

export const useRevenueSeries = (period: string) =>
  useQuery<RevenueSeries>({ queryKey: ["dashboard", "revenue", period], queryFn: () => api.get(`/dashboard/revenue-series${P(period)}`) });

export const useRomiByChannel = () =>
  useQuery<RomiByChannel[]>({ queryKey: ["dashboard", "romi-by-channel"], queryFn: () => api.get("/dashboard/romi-by-channel") });

export const useManagers = () =>
  useQuery<Manager[]>({ queryKey: ["dashboard", "managers"], queryFn: () => api.get("/dashboard/managers") });

export const useLeads = (mgr: string, source: string, risk: string | null, period: string) =>
  useQuery<Lead[]>({
    queryKey: ["dashboard", "leads", mgr, source, risk, period],
    queryFn: () => {
      const q = new URLSearchParams();
      if (mgr && mgr !== "all") q.set("mgr", mgr);
      if (source && source !== "all") q.set("source", source);
      if (risk) q.set("risk", risk);
      if (period) q.set("period", period);
      const qs = q.toString();
      return api.get(`/dashboard/leads${qs ? `?${qs}` : ""}`);
    },
  });
