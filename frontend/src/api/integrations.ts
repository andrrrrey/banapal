// Хуки страницы настроек интеграций (TanStack Query).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";

export type DataSource = "mock" | "real";

export interface IntegrationField {
  key: string;
  label: string;
  hint: string;
  secret: boolean;
  placeholder: string;
  filled: boolean;
  value: string; // для секретов — маска; для остального — само значение
}

export interface IntegrationProvider {
  key: string;
  name: string;
  subtitle: string;
  docs: string;
  configured: boolean;
  fields: IntegrationField[];
}

export interface IntegrationsConfig {
  data_source: DataSource;
  providers: IntegrationProvider[];
}

export type CheckStatus = "ok" | "error" | "not_configured";

export interface CheckResult {
  provider: string;
  status: CheckStatus;
  message: string;
  detail: string;
  checked_at: string;
}

export interface SavePayload {
  values?: Record<string, string>;
  clear?: string[];
  data_source?: DataSource;
}

export function useIntegrations() {
  return useQuery<IntegrationsConfig>({
    queryKey: ["integrations"],
    queryFn: () => api.get("/integrations"),
  });
}

// Лёгкий запрос текущего источника данных (для плашки режима в топбаре).
export function useDataSource() {
  return useQuery<{ data_source: DataSource }>({
    queryKey: ["integrations", "data-source"],
    queryFn: () => api.get("/integrations/data-source"),
    staleTime: 30_000,
  });
}

export function useSaveIntegrations() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SavePayload) => api.put<IntegrationsConfig>("/integrations", payload),
    onSuccess: (data) => {
      qc.setQueryData(["integrations"], data);
      qc.setQueryData(["integrations", "data-source"], { data_source: data.data_source });
    },
  });
}

export function useCheckIntegration() {
  return useMutation({
    mutationFn: (provider: string) => api.post<CheckResult>(`/integrations/${provider}/check`),
  });
}

export function useCheckAll() {
  return useMutation({
    mutationFn: () => api.post<Record<string, CheckResult>>("/integrations/check"),
  });
}
