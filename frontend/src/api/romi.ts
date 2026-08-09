// Хуки ROMI и рекомендаций (TanStack Query).

import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export interface RomiChannelChart {
  name: string; short_name: string; spend: number | null; margin: number; color: string;
}
export interface CampaignBubble {
  name: string; spend: number | null; romi: number | null; revenue: number; color: string;
}
export interface BudgetRec {
  ic: string; svg: string; title: string; tag_label: string; tag_class: string;
  text: string; why: string; impact: string; src: string[]; conf: string; dep: boolean;
}
export interface MinusWord {
  phrase: string; camp: string; level: string; shows: number; clicks: number;
  spend: number; spend_display: string; conv: number; deals: number;
  reason: string; conf: string; status: string;
}
export interface MinusWords {
  summary: { count: number; spend: number; spend_display: string; camps: number };
  items: MinusWord[];
}

export const useRomiChannels = () =>
  useQuery<RomiChannelChart[]>({ queryKey: ["romi", "by-channel"], queryFn: () => api.get("/romi/by-channel") });

export const useCampaignsBubble = () =>
  useQuery<CampaignBubble[]>({ queryKey: ["romi", "campaigns"], queryFn: () => api.get("/romi/campaigns") });

export const useBudgetRecs = () =>
  useQuery<BudgetRec[]>({ queryKey: ["romi", "budget-recs"], queryFn: () => api.get("/romi/budget-recs") });

export const useMinusWords = () =>
  useQuery<MinusWords>({ queryKey: ["romi", "minus-words"], queryFn: () => api.get("/romi/minus-words") });
