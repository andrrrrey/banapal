import { Select } from "antd";
import { useLocation } from "react-router-dom";

import { useFilterOptions } from "@/api/dashboard";
import { useFilters } from "@/state/filters";

// Панель фильтров. Опции менеджеров/каналов/источников — реальные из данных БД
// (в боевом режиме отражают подключённые интеграции; в демо — демо-значения).
const PERIODS = [
  { key: "today", label: "Сегодня" },
  { key: "7", label: "7 дней" },
  { key: "30", label: "30 дней" },
  { key: "quarter", label: "Квартал" },
];

// Какие контролы фильтров релевантны на каждой странице. На страницах, которых
// нет в конфиге (ROMI, AI, Мониторинг, Интеграции, Админ), панель не показывается —
// эти разделы не используют фильтры.
type Control = "period" | "channel" | "mgr" | "source";
const PAGE_FILTERS: Record<string, Control[]> = {
  "/dashboard": ["period", "mgr", "source"],
  "/analytics": ["period", "channel"],
};

function opts(all: string, values: string[]) {
  return [{ value: "all", label: all }, ...values.map((v) => ({ value: v, label: v }))];
}

export function FilterBar() {
  const f = useFilters();
  const o = useFilterOptions();
  const location = useLocation();

  const path = Object.keys(PAGE_FILTERS).find((p) => location.pathname.startsWith(p));
  const controls = path ? PAGE_FILTERS[path] : [];
  if (controls.length === 0) return null;

  return (
    <div className="filterbar">
      {controls.includes("period") ? (
        <div className="seg">
          {PERIODS.map((p) => (
            <button key={p.key} className={f.period === p.key ? "on" : ""} onClick={() => f.setPeriod(p.key)}>
              {p.label}
            </button>
          ))}
        </div>
      ) : null}
      <div className="spacer" />
      {controls.includes("channel") ? (
        <Select
          className="fb-select"
          value={f.channel}
          onChange={f.setChannel}
          options={opts("Все каналы", o.data?.channels ?? [])}
        />
      ) : null}
      {controls.includes("mgr") ? (
        <Select
          className="fb-select"
          value={f.mgr}
          onChange={(v) => { f.setMgr(v); f.setLeadFilter(null); }}
          options={opts("Все менеджеры", o.data?.managers ?? [])}
        />
      ) : null}
      {controls.includes("source") ? (
        <Select
          className="fb-select"
          value={f.source}
          onChange={f.setSource}
          options={opts("Все источники", o.data?.sources ?? [])}
        />
      ) : null}
    </div>
  );
}
