import { Select } from "antd";

import { useFilters } from "@/state/filters";

// Панель фильтров из прототипа, связанная с глобальным состоянием.
const PERIODS = [
  { key: "today", label: "Сегодня" },
  { key: "7", label: "7 дней" },
  { key: "30", label: "30 дней" },
  { key: "quarter", label: "Квартал" },
];

const CHANNELS = [
  "Все каналы", "Яндекс Директ — Поиск", "Яндекс Директ — РСЯ",
  "Органический поиск", "Прямые заходы", "Соцсети",
];
const MANAGERS = ["Все менеджеры", "Азалия Хаметова", "Дмитрий Крылов", "Ольга Северцева", "Тимур Рахимов"];
const SOURCES = ["Все источники", "Поиск", "РСЯ", "Сайт", "Звонок"];

function opts(values: string[], allValue: string) {
  return values.map((v, i) => ({ value: i === 0 ? allValue : v, label: v }));
}

export function FilterBar() {
  const f = useFilters();

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
        value={f.channel}
        onChange={f.setChannel}
        options={opts(CHANNELS, "all")}
        style={{ width: 200 }}
      />
      <Select
        value={f.mgr}
        onChange={(v) => { f.setMgr(v); f.setLeadFilter(null); }}
        options={opts(MANAGERS, "all")}
        style={{ width: 190 }}
      />
      <Select
        value={f.source}
        onChange={f.setSource}
        options={opts(SOURCES, "all")}
        style={{ width: 160 }}
      />
    </div>
  );
}
