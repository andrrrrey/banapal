import { App, Button, Input, Segmented, Spin } from "antd";
import { useEffect, useMemo, useState } from "react";

import {
  type CheckResult,
  type CheckStatus,
  type DataSource,
  type IntegrationField,
  type IntegrationProvider,
  type IntegrationsConfig,
  useCheckAll,
  useCheckIntegration,
  useIntegrations,
  useSaveIntegrations,
} from "@/api/integrations";

/* --- Значок статуса подключения --- */
function statusMeta(
  provider: IntegrationProvider,
  check?: CheckResult,
): { cls: string; text: string } {
  if (check) {
    if (check.status === "ok") return { cls: "ok", text: "Подключено" };
    if (check.status === "not_configured") return { cls: "idle", text: "Не заполнено" };
    return { cls: "err", text: "Ошибка" };
  }
  if (!provider.configured) return { cls: "idle", text: "Не заполнено" };
  return { cls: "warn", text: "Не проверено" };
}

function StatusBadge({ cls, text }: { cls: string; text: string }) {
  return (
    <span className={`intg-badge ${cls}`}>
      <span className="dot" />
      {text}
    </span>
  );
}

/* --- Поле ввода одного креда --- */
function FieldInput({
  field,
  value,
  onChange,
}: {
  field: IntegrationField;
  value: string;
  onChange: (v: string) => void;
}) {
  const savedHint = field.secret && field.filled;
  const placeholder = savedHint
    ? `Сохранено (${field.value}). Оставьте пустым, чтобы не менять`
    : field.placeholder || "Не задано";

  return (
    <div className="field intg-field">
      <label>{field.label}</label>
      {field.secret ? (
        <Input.Password
          value={value}
          placeholder={placeholder}
          autoComplete="new-password"
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <Input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      )}
      {field.hint ? <span className="intg-hint">{field.hint}</span> : null}
    </div>
  );
}

/* --- Инициализация черновика из конфигурации --- */
function initialDraft(cfg: IntegrationsConfig): Record<string, string> {
  const d: Record<string, string> = {};
  for (const p of cfg.providers) {
    for (const f of p.fields) d[f.key] = f.secret ? "" : f.value;
  }
  return d;
}

export default function IntegrationsPage() {
  const q = useIntegrations();
  const save = useSaveIntegrations();
  const checkOne = useCheckIntegration();
  const checkAll = useCheckAll();
  const { message } = App.useApp();

  const [draft, setDraft] = useState<Record<string, string>>({});
  const [dataSource, setDataSource] = useState<DataSource>("mock");
  const [checks, setChecks] = useState<Record<string, CheckResult>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (q.data) {
      setDraft(initialDraft(q.data));
      setDataSource(q.data.data_source);
    }
  }, [q.data]);

  const cfg = q.data;

  const dirty = useMemo(() => {
    if (!cfg) return false;
    if (dataSource !== cfg.data_source) return true;
    for (const p of cfg.providers) {
      for (const f of p.fields) {
        const initial = f.secret ? "" : f.value;
        if ((draft[f.key] ?? "") !== initial) return true;
      }
    }
    return false;
  }, [cfg, draft, dataSource]);

  if (!cfg) {
    return (
      <div style={{ minHeight: "40vh", display: "grid", placeItems: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  const setField = (key: string, v: string) => setDraft((d) => ({ ...d, [key]: v }));

  const buildValues = (): Record<string, string> => {
    const values: Record<string, string> = {};
    for (const p of cfg.providers) {
      for (const f of p.fields) {
        const cur = draft[f.key] ?? "";
        if (f.secret) {
          if (cur.trim() !== "") values[f.key] = cur; // пустой секрет = «не менять»
        } else if (cur !== f.value) {
          values[f.key] = cur; // несекрет можно и очистить пустой строкой
        }
      }
    }
    return values;
  };

  const onSave = async () => {
    try {
      await save.mutateAsync({
        values: buildValues(),
        data_source: dataSource,
      });
      message.success("Настройки интеграций сохранены");
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const applyCheck = (res: CheckResult) => {
    setChecks((c) => ({ ...c, [res.provider]: res }));
    return res;
  };

  const onCheckOne = async (provider: string) => {
    setBusy((b) => ({ ...b, [provider]: true }));
    try {
      const res = await checkOne.mutateAsync(provider);
      applyCheck(res);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy((b) => ({ ...b, [provider]: false }));
    }
  };

  const onCheckAll = async () => {
    try {
      const res = await checkAll.mutateAsync();
      setChecks(res);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <>
      {/* Источник данных */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-h">
          <h3>Источник данных</h3>
          <span className="sub">чем наполнять систему</span>
        </div>
        <div className="card-p intg-source">
          <Segmented
            value={dataSource}
            onChange={(v) => setDataSource(v as DataSource)}
            options={[
              { label: "Демо-данные", value: "mock" },
              { label: "Боевые интеграции", value: "real" },
            ]}
          />
          <p className="intg-source-note">
            {dataSource === "mock"
              ? "Система работает на демонстрационных данных прототипа. Доступы ниже можно заполнить заранее."
              : "Система использует боевые интеграции. Заполните и проверьте доступы ниже — иначе выгрузка данных завершится ошибкой."}
          </p>
        </div>
      </div>

      {/* Карточки интеграций */}
      <div className="grid intg-grid">
        {cfg.providers.map((p) => {
          const check = checks[p.key];
          const meta = statusMeta(p, check);
          return (
            <div className="card intg-card" key={p.key}>
              <div className="card-h">
                <div>
                  <h3>{p.name}</h3>
                  <span className="sub">{p.subtitle}</span>
                </div>
                <StatusBadge cls={meta.cls} text={meta.text} />
              </div>
              <div className="card-p">
                {p.fields.map((f) => (
                  <FieldInput
                    key={f.key}
                    field={f}
                    value={draft[f.key] ?? ""}
                    onChange={(v) => setField(f.key, v)}
                  />
                ))}

                <div className="intg-docs">{p.docs}</div>

                {check ? (
                  <div className={`intg-result ${resultCls(check.status)}`}>
                    <b>{check.message}</b>
                    {check.detail ? <span> {check.detail}</span> : null}
                  </div>
                ) : null}

                <div className="intg-actions">
                  <Button
                    size="small"
                    loading={busy[p.key]}
                    onClick={() => onCheckOne(p.key)}
                  >
                    Проверить подключение
                  </Button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Нижняя панель действий */}
      <div className="intg-footer">
        <span className="intg-footer-note">
          Проверка использует сохранённые доступы. Изменили поля — сначала сохраните.
        </span>
        <div style={{ display: "flex", gap: 10 }}>
          <Button onClick={onCheckAll} loading={checkAll.isPending}>
            Проверить все
          </Button>
          <Button type="primary" onClick={onSave} loading={save.isPending} disabled={!dirty}>
            Сохранить
          </Button>
        </div>
      </div>
    </>
  );
}

function resultCls(status: CheckStatus): string {
  if (status === "ok") return "ok";
  if (status === "not_configured") return "idle";
  return "err";
}
