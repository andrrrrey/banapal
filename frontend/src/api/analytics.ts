// Хуки сквозной аналитики (TanStack Query).

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "./client";

// Общие опции устойчивости для витрин аналитики. Причина: страница читает данные
// «на лету» из БД, и одиночный сетевой/серверный сбой (кратковременный при
// параллельной сверке сделок) переводил запрос в ошибку, а вёрстка показывала
// вечный спиннер до ручной перезагрузки — данные будто «пропадали».
//   • keepPreviousData — при смене периода/канала не мигаем в пустоту, держим
//     прошлые данные, пока грузятся новые;
//   • staleTime — переход между разделами не вызывает жёсткого перезапроса;
//   • retry с бэкоффом — временный сбой сам восстанавливается, без перезагрузки.
const RESILIENT = {
  placeholderData: keepPreviousData,
  staleTime: 15_000,
  retry: 3,
  retryDelay: (attempt: number) => Math.min(1000 * 2 ** attempt, 8000),
} as const;

export interface ChainStep {
  label: string; sub: string; color: string; width: number; glow: boolean;
  display: string; conversion: number | null;
  // Ненулевой drill — шаг кликабелен (напр. «payments» раскрывает оплаты).
  drill?: string | null;
}

export interface PaymentItem {
  name: string; mgr: string; src: string; date: string;
  amount: number; amount_display: string;
}
export interface PaymentsBreakdown {
  source: string;
  source_label: string;
  source_hint: string;
  exact: boolean;
  count: number;
  total: number;
  total_display: string;
  items: PaymentItem[];
}

export interface RomiTag { display: string; cls: string; value: number | null; }
export interface Action { label: string; cls: string; note: string; }

export interface Campaign {
  name: string; spend: number | null; spend_display: string;
  leads: number; deals: number; payments: number;
  revenue: number; revenue_display: string; margin: number; margin_display: string;
  romi: RomiTag; action: Action;
}
export interface ChannelRow extends Omit<Campaign, "name"> {
  name: string; color: string; campaigns: Campaign[];
}

// paySrc — необязательный override источника оплат (фильтр экрана). null → сервер
// использует настроенный по умолчанию.
const paySrcQs = (paySrc?: string | null) =>
  paySrc ? `&payments_source=${encodeURIComponent(paySrc)}` : "";

export const useChain = (period: string, paySrc?: string | null) =>
  useQuery<ChainStep[]>({
    queryKey: ["analytics", "chain", period, paySrc ?? "default"],
    queryFn: () =>
      api.get(`/analytics/chain?period=${encodeURIComponent(period)}${paySrcQs(paySrc)}`),
    ...RESILIENT,
  });

export const useChannels = (channel: string, period: string) =>
  useQuery<ChannelRow[]>({
    queryKey: ["analytics", "channels", channel, period],
    queryFn: () =>
      api.get(
        `/analytics/channels?channel=${encodeURIComponent(channel)}` +
          `&period=${encodeURIComponent(period)}`,
      ),
    ...RESILIENT,
  });

// Расшифровка «Оплаты клиентов» — грузится только когда открыто окно (enabled).
export const usePayments = (period: string, enabled: boolean, paySrc?: string | null) =>
  useQuery<PaymentsBreakdown>({
    queryKey: ["analytics", "payments", period, paySrc ?? "default"],
    queryFn: () =>
      api.get(`/analytics/payments?period=${encodeURIComponent(period)}${paySrcQs(paySrc)}`),
    enabled,
    staleTime: 15_000,
    retry: 2,
  });
