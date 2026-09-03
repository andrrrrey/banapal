import { createContext, type ReactNode, useContext, useMemo, useState } from "react";

// Глобальные фильтры дашборда/аналитики (период, канал, менеджер, источник)
// и фильтр таблицы лидов. Совпадают с фильтрами прототипа.
export interface FiltersState {
  period: string;
  channel: string;
  mgr: string;
  source: string;
  leadFilter: string | null;
  // Источник факта оплаты — фильтр экрана «Сквозная аналитика». null = использовать
  // настроенный по умолчанию (страница «Интеграции»); иначе — явный выбор на экране.
  paymentsSource: string | null;
  setPeriod: (v: string) => void;
  setChannel: (v: string) => void;
  setMgr: (v: string) => void;
  setSource: (v: string) => void;
  setLeadFilter: (v: string | null) => void;
  setPaymentsSource: (v: string | null) => void;
}

const FiltersContext = createContext<FiltersState | null>(null);

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [period, setPeriod] = useState("30");
  const [channel, setChannel] = useState("all");
  const [mgr, setMgr] = useState("all");
  const [source, setSource] = useState("all");
  const [leadFilter, setLeadFilter] = useState<string | null>(null);
  const [paymentsSource, setPaymentsSource] = useState<string | null>(null);

  const value = useMemo(
    () => ({
      period, channel, mgr, source, leadFilter, paymentsSource,
      setPeriod, setChannel, setMgr, setSource, setLeadFilter, setPaymentsSource,
    }),
    [period, channel, mgr, source, leadFilter, paymentsSource],
  );

  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters(): FiltersState {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("useFilters must be used within FiltersProvider");
  return ctx;
}
