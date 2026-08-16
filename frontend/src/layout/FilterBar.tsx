import { Select } from "antd";

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

function opts(all: string, values: string[]) {
  return [{ value: "all", label: all }, ...values.map((v) => ({ value: v, label: v }))];
}

export function FilterBar() {
  const f = useFilters();
  const o = useFilterOptions();

  return (
    <div className="filterbar">
      <div className="seg">
        {PERIODS.map((p) => (
          <button key={p.key} className={f.period === p.key ? "on" : ""} onClick={() => f.setPeriod(p.key)}>
            {p.label}
          </button>
        ))}
      </div>
      <div className="spacer" />
      <Select
        className="fb-select"
        value={f.channel}
        onChange={f.setChannel}
        options={opts("Все каналы", o.data?.channels ?? [])}
      />
      <Select
        className="fb-select"
        value={f.mgr}
        onChange={(v) => { f.setMgr(v); f.setLeadFilter(null); }}
        options={opts("Все менеджеры", o.data?.managers ?? [])}
      />
      <Select
        className="fb-select"
        value={f.source}
        onChange={f.setSource}
        options={opts("Все источники", o.data?.sources ?? [])}
      />
    </div>
  );
}
