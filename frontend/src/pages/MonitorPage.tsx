import { App, Button, Spin } from "antd";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useCreateTask, useMonitorStats, useReview, useViolations } from "@/api/monitor";
import { ViolationRow } from "@/components/ViolationRow";

const PTYPE_LABEL: Record<string, string> = {
  overdue_contact: "Просрочка первого контакта",
  no_task: "Сделки без задачи",
  stuck: "Зависшие сделки",
  no_recontact: "Без повторного касания",
  fields: "Незаполненные поля",
  dup: "Возможные дубли",
  spam: "Подозрительный спам/отказ",
  refusal: "Подозрительный спам/отказ",
};

// Подписи фильтра по серьёзности (плашки статистики) — совпадают с подписями плашек.
const SEV_LABEL: Record<string, string> = {
  over: "Критичные просрочки",
  money: "Деньги под риском",
  warn: "Требуют внимания",
  review: "На проверке",
};

export default function MonitorPage() {
  const [params, setParams] = useSearchParams();
  const filter = params.get("ptype");
  const sev = params.get("sev");
  // Доп. фильтр по типу нарушения внутри группы плашки (например «Не заполнены
  // обязательные поля» или «Возможный дубль» среди «Требуют внимания»).
  const sub = params.get("sub");
  const isReviewFilter = filter === "spam" || filter === "refusal" || sev === "review";

  const stats = useMonitorStats();
  // Список regular тянем целиком (по ptype), а фильтр по серьёзности применяем на
  // клиенте — severity уже есть в каждой строке, отдельный запрос не нужен.
  const violations = useViolations(filter);
  const review = useReview();
  const createTask = useCreateTask();
  const { message } = App.useApp();
  const [done, setDone] = useState<Set<string>>(new Set());

  // Фильтрация списка нарушений по серьёзности (клик по плашке статистики).
  const sevRows = useMemo(() => {
    const data = violations.data ?? [];
    if (sev === "over") return data.filter((v) => v.severity === "over");
    if (sev === "warn") return data.filter((v) => v.severity === "warn");
    if (sev === "money")
      return data
        .filter((v) => v.severity === "over" && v.amount > 0)
        .sort((a, b) => b.amount - a.amount);
    return data;
  }, [violations.data, sev]);

  // Доп. фильтры внутри группы: типы нарушений (ptype), присутствующие в выборке
  // плашки, с числом сделок в каждом. Их набор зависит от плашки — у «критичных
  // просрочек» одни типы, у «требуют внимания» другие (незаполненные поля, дубли…).
  const subFilters = useMemo(() => {
    const map = new Map<string, { ptype: string; label: string; count: number }>();
    for (const v of sevRows) {
      const e = map.get(v.ptype) ?? { ptype: v.ptype, label: v.kind_label, count: 0 };
      e.count += 1;
      map.set(v.ptype, e);
    }
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [sevRows]);

  // Доп. фильтр показываем только когда активна плашка со списком (over/warn/money)
  // и типов внутри больше одного — иначе выбирать нечего.
  const showSubFilters =
    (sev === "over" || sev === "warn" || sev === "money") && subFilters.length > 1;

  const rows = sub ? sevRows.filter((v) => v.ptype === sub) : sevRows;

  const PAGE_SIZE = 20;
  const [page, setPage] = useState(0);
  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  // Доп. фильтры для оценочных нарушений «На проверке» (типы spam/refusal).
  const reviewSubFilters = useMemo(() => {
    const map = new Map<string, { ptype: string; label: string; count: number }>();
    for (const v of review.data ?? []) {
      const e = map.get(v.ptype) ?? { ptype: v.ptype, label: v.kind_label, count: 0 };
      e.count += 1;
      map.set(v.ptype, e);
    }
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [review.data]);
  const showReviewSubFilters = sev === "review" && reviewSubFilters.length > 1;

  // Пагинация списка «Требует решения руководителя» (оценочные — их много).
  const [reviewPage, setReviewPage] = useState(0);
  const reviewData = review.data ?? [];
  const reviewFiltered =
    sev === "review" && sub ? reviewData.filter((v) => v.ptype === sub) : reviewData;
  const reviewTotal = reviewFiltered.length;
  const reviewPages = Math.max(1, Math.ceil(reviewTotal / PAGE_SIZE));
  const reviewRows = reviewFiltered.slice(
    reviewPage * PAGE_SIZE, reviewPage * PAGE_SIZE + PAGE_SIZE);

  // Сброс страниц при смене фильтра или объёма данных.
  useEffect(() => { setPage(0); }, [filter, sev, sub, total]);
  useEffect(() => { setReviewPage(0); }, [filter, sub, reviewTotal]);

  const clearFilter = () => setParams({});

  // Клик по плашке статистики: ставим ?sev=key (фильтры ptype и sev взаимоисключающие);
  // повторный клик по активной плашке снимает фильтр. Доп. фильтр (sub) при этом
  // сбрасывается — у другой плашки свой набор типов.
  const onStatClick = (key?: string) => {
    if (!key) return;
    setParams(sev === key ? {} : { sev: key });
  };

  // Клик по чипу доп. фильтра: добавляет ?sub=ptype к активной плашке; повторный
  // клик по активному чипу снимает доп. фильтр (остаётся только плашка).
  const onSubClick = (ptype: string) => {
    const next: Record<string, string> = {};
    if (sev) next.sev = sev;
    if (sub !== ptype) next.sub = ptype;
    setParams(next);
  };

  const onTask = (ref: string) => {
    createTask.mutate(ref, {
      onSuccess: (res) => {
        setDone((prev) => new Set(prev).add(ref));
        // В демо-режиме в портал ничего не уходит — не выдаём это за созданную задачу.
        if (res.mock) {
          message.warning(
            `Демо-режим: задача записана локально, в Битрикс24 не создана · ${res.assignee}`,
          );
          return;
        }
        message.success(
          `Задача и дело созданы в сделке Битрикс24 · ${res.assignee}`,
        );
      },
      onError: (e) => message.error((e as Error).message || "Не удалось создать задачу"),
    });
  };

  const showReviewCard = (!filter && !sev) || isReviewFilter;

  return (
    <>
      {filter || sev ? (
        <div style={{ marginBottom: 14 }}>
          <span className="filterpill">
            Фильтр: <b>{filter ? (PTYPE_LABEL[filter] ?? filter) : (SEV_LABEL[sev!] ?? sev)}</b>
            {sub ? <b> · {PTYPE_LABEL[sub] ?? sub}</b> : null}
            <button onClick={clearFilter}>×</button>
          </span>
        </div>
      ) : null}

      <div className="grid mon-stats">
        {stats.data?.stats.map((s, i) => (
          <div
            key={i}
            className={`mstat ${s.cls}${s.key ? " clickable" : ""}${sev === s.key && s.key ? " active" : ""}`}
            onClick={s.key ? () => onStatClick(s.key) : undefined}
            role={s.key ? "button" : undefined}
            tabIndex={s.key ? 0 : undefined}
            onKeyDown={
              s.key
                ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onStatClick(s.key);
                    }
                  }
                : undefined
            }
          >
            <div className="mn num">{s.n}</div>
            <div className="ml">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-h">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <h3>Нарушения регламента</h3>
            <span className="live">
              <span className="p" />В реальном времени
            </span>
          </div>
        </div>
        {showSubFilters ? (
          <div className="subfilters">
            <button
              className={`subchip${!sub ? " on" : ""}`}
              onClick={() => onSubClick(sub ?? "")}
              disabled={!sub}
            >
              Все типы <span className="subchip-n">{sevRows.length}</span>
            </button>
            {subFilters.map((sf) => (
              <button
                key={sf.ptype}
                className={`subchip${sub === sf.ptype ? " on" : ""}`}
                onClick={() => onSubClick(sf.ptype)}
              >
                {sf.label} <span className="subchip-n">{sf.count}</span>
              </button>
            ))}
          </div>
        ) : null}
        <div className="deal-list">
          {violations.isLoading ? (
            <div style={{ padding: 40, textAlign: "center" }}>
              <Spin />
            </div>
          ) : isReviewFilter ? (
            <div className="empty-note">
              Оценочные нарушения этого типа показаны в блоке «Требует решения руководителя» ниже.
            </div>
          ) : total ? (
            pageRows.map((v, i) => (
              <ViolationRow
                key={page * PAGE_SIZE + i}
                v={v}
                onTask={onTask}
                taskPending={createTask.isPending}
                taskDone={done.has(v.ref)}
              />
            ))
          ) : (
            <div className="empty-note">Нет нарушений этого типа</div>
          )}
        </div>
        {total > PAGE_SIZE ? (
          <div className="pager">
            <Button size="small" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              ← Назад
            </Button>
            <span className="pager-info">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} из {total}
            </span>
            <Button size="small" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>
              Вперёд →
            </Button>
          </div>
        ) : null}
      </div>

      {showReviewCard ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-h">
            <h3>Требует решения руководителя</h3>
            <span className="sub">оценочные нарушения — автоклассификации не поддаются</span>
          </div>
          {showReviewSubFilters ? (
            <div className="subfilters">
              <button
                className={`subchip${!sub ? " on" : ""}`}
                onClick={() => onSubClick(sub ?? "")}
                disabled={!sub}
              >
                Все типы <span className="subchip-n">{reviewData.length}</span>
              </button>
              {reviewSubFilters.map((sf) => (
                <button
                  key={sf.ptype}
                  className={`subchip${sub === sf.ptype ? " on" : ""}`}
                  onClick={() => onSubClick(sf.ptype)}
                >
                  {sf.label} <span className="subchip-n">{sf.count}</span>
                </button>
              ))}
            </div>
          ) : null}
          <div className="deal-list">
            {reviewTotal ? (
              reviewRows.map((v, i) => <ReviewRow key={reviewPage * PAGE_SIZE + i} v={v} />)
            ) : (
              <div className="empty-note">Нет оценочных нарушений на проверке</div>
            )}
          </div>
          {reviewTotal > PAGE_SIZE ? (
            <div className="pager">
              <Button size="small" disabled={reviewPage === 0}
                onClick={() => setReviewPage((p) => p - 1)}>
                ← Назад
              </Button>
              <span className="pager-info">
                {reviewPage * PAGE_SIZE + 1}–{Math.min((reviewPage + 1) * PAGE_SIZE, reviewTotal)} из{" "}
                {reviewTotal}
              </span>
              <Button size="small" disabled={reviewPage >= reviewPages - 1}
                onClick={() => setReviewPage((p) => p + 1)}>
                Вперёд →
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
    </>
  );
}

function ReviewRow({ v }: { v: import("@/api/monitor").Violation }) {
  const { message } = App.useApp();
  return (
    <div className="deal">
      <div className="lft" style={{ background: "var(--violet)" }} />
      <div className="body">
        <div className="name">
          {v.name}
          <span className={`tag ${v.kind_class}`}>{v.kind_label}</span>
        </div>
        <div className="meta">
          <span>👤 {v.mgr}</span>
          <span>◎ {v.src}</span>
        </div>
        <div className="ai-note">{v.ai}</div>
      </div>
      <div className="act" style={{ display: "flex", gap: 8 }}>
        <Button size="small" onClick={() => message.success("Помечено как обоснованное")}>
          Обоснованно
        </Button>
        <Button type="primary" size="small" onClick={() => message.success("Задача руководителю поставлена")}>
          На разбор
        </Button>
      </div>
    </div>
  );
}
