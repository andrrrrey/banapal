import { Select } from "antd";
import { useState } from "react";

// Панель фильтров из прототипа. На Этапе A — визуальный каркас;
// привязка к данным (период, канал, менеджер, источник) — на Этапе D.

const PERIODS = [
  { key: "today", label: "Сегодня" },
  { key: "7", label: "7 дней" },
  { key: "30", label: "30 дней" },
  { key: "quarter", label: "Квартал" },
];

const CHANNELS = [
  "Все каналы",
  "Яндекс Директ — Поиск",
  "Яндекс Директ — РСЯ",
  "Органический поиск",
  "Прямые заходы",
  "Соцсети",
];
const MANAGERS = ["Все менеджеры", "Азалия Хаметова", "Дмитрий Крылов", "Ольга Северцева", "Тимур Рахимов"];
const SOURCES = ["Все источники", "Поиск", "РСЯ", "Сайт", "Звонок"];

function toOptions(values: string[]) {
  return values.map((v) => ({ value: v, label: v }));
}

export function FilterBar() {
  const [period, setPeriod] = useState("30");

  return (
    <div className="filterbar">
      <div className="seg">
        {PERIODS.map((p) => (
          <button key={p.key} className={period === p.key ? "on" : ""} onClick={() => setPeriod(p.key)}>
            {p.label}
          </button>
        ))}
      </div>
      <div className="spacer" />
      <Select defaultValue="Все каналы" options={toOptions(CHANNELS)} style={{ width: 200 }} />
      <Select defaultValue="Все менеджеры" options={toOptions(MANAGERS)} style={{ width: 190 }} />
      <Select defaultValue="Все источники" options={toOptions(SOURCES)} style={{ width: 160 }} />
    </div>
  );
}
