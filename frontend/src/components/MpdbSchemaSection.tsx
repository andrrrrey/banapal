import { App, Button, Input } from "antd";
import { useMemo, useState } from "react";

import { type MpdbTable, useMoyskladSchema } from "@/api/integrations";

// Раздел просмотра структуры Postgres-реплики МойСклад (mpdb).
// Кнопка запрашивает у бэкенда список таблиц/колонок (интроспекция information_schema),
// чтобы сопоставить реальные имена с запросами адаптера без ручного описания от заказчика.
export function MpdbSchemaSection() {
  const schema = useMoyskladSchema();
  const { message } = App.useApp();
  const [tables, setTables] = useState<MpdbTable[] | null>(null);
  const [paymentsTable, setPaymentsTable] = useState<string | null>(null);
  const [q, setQ] = useState("");

  const onLoad = async () => {
    try {
      const res = await schema.mutateAsync();
      if (!res.ok) {
        message.error(`Не удалось прочитать структуру mpdb: ${res.error ?? "ошибка"}`);
        setTables(null);
        return;
      }
      setTables(res.tables);
      setPaymentsTable(res.payments_table ?? null);
      if (!res.tables.length) message.warning("В реплике не найдено пользовательских таблиц");
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const filtered = useMemo(() => {
    if (!tables) return [];
    const needle = q.trim().toLowerCase();
    if (!needle) return tables;
    // Фильтр по имени таблицы ИЛИ по имени любой её колонки.
    return tables
      .map((t) => {
        const tableHit = `${t.schema}.${t.table}`.toLowerCase().includes(needle);
        if (tableHit) return t;
        const cols = t.columns.filter((c) => c.name.toLowerCase().includes(needle));
        return cols.length ? { ...t, columns: cols } : null;
      })
      .filter((t): t is MpdbTable => t !== null);
  }, [tables, q]);

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="card-h">
        <div>
          <h3>Структура реплики МойСклад (mpdb)</h3>
          <span className="sub">таблицы и колонки Postgres-реплики</span>
        </div>
        <Button size="small" onClick={onLoad} loading={schema.isPending}>
          Показать таблицы mpdb
        </Button>
      </div>
      <div className="card-p">
        {tables === null ? (
          <p className="intg-source-note">
            Нажмите «Показать таблицы mpdb», чтобы прочитать структуру реплики напрямую
            из БД (нужен заполненный DSN и доступ к базе). Ручное описание таблиц от
            заказчика не требуется — имена читаются из information_schema.
          </p>
        ) : (
          <>
            <div className={`mpdb-pay ${paymentsTable ? "ok" : "warn"}`}>
              {paymentsTable ? (
                <>
                  Таблица оплат найдена: <b>{paymentsTable}</b>. Источник «Оплаты: МойСклад»
                  соберёт входящие платежи из неё при следующем пересчёте.
                </>
              ) : (
                <>
                  Таблица входящих платежей в реплике <b>не найдена</b> (ожидается имя вида
                  <code> *paymentin*</code> / <code>*cashin*</code>). Поэтому «Оплаты: МойСклад» = 0.
                  Варианты: добавить платежи в состав реплики, задать API-токен МойСклад как
                  резерв, либо считать оплатой отгрузки (ms_demands) — подскажите, как считаете
                  оплату, и я подключу нужную таблицу.
                </>
              )}
            </div>
            <div className="mpdb-toolbar">
              <Input
                allowClear
                placeholder="Поиск по таблице или колонке…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                style={{ maxWidth: 340 }}
              />
              <span className="mpdb-count">
                таблиц: {tables.length}
                {q.trim() ? ` · найдено: ${filtered.length}` : ""}
              </span>
            </div>
            <div className="mpdb-tables">
              {filtered.map((t) => (
                <div key={`${t.schema}.${t.table}`} className="mpdb-table">
                  <div className="mpdb-table-name">
                    {t.schema !== "public" ? `${t.schema}.` : ""}
                    {t.table}
                    <span className="mpdb-col-count">{t.columns.length} колонок</span>
                  </div>
                  <div className="mpdb-cols">
                    {t.columns.map((c) => (
                      <span key={c.name} className="mpdb-col" title={c.type}>
                        <b>{c.name}</b>
                        <i>{c.type}</i>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {filtered.length === 0 ? (
                <p className="intg-source-note">Ничего не найдено по запросу.</p>
              ) : null}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
