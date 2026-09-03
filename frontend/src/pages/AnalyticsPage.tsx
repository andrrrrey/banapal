import { Button, Modal, Spin, Table, Tag } from "antd";
import type { UseQueryResult } from "@tanstack/react-query";
import { useState } from "react";

import { useChain, useChannels, usePayments } from "@/api/analytics";
import { ChainView } from "@/components/ChainView";
import { ChannelsTable } from "@/components/ChannelsTable";
import { EmptyState } from "@/components/EmptyState";
import { useFilters } from "@/state/filters";

// Заглушка на случай сбоя запроса без ранее загруженных данных: показываем
// причину и кнопку повтора вместо вечного спиннера. Раньше ошибочный запрос
// (кратковременный сбой при параллельной сверке) оставлял спиннер до ручной
// перезагрузки — это и выглядело как «данные пропали».
function LoadFail({ query }: { query: UseQueryResult<unknown> }) {
  return (
    <div style={{ padding: 30, textAlign: "center" }}>
      <div style={{ marginBottom: 12, color: "var(--muted)", fontSize: 13 }}>
        Не удалось загрузить данные. Подключения могут быть в порядке — попробуйте ещё раз.
      </div>
      <Button size="small" onClick={() => query.refetch()} loading={query.isFetching}>
        Повторить
      </Button>
    </div>
  );
}

export default function AnalyticsPage() {
  const f = useFilters();
  const chain = useChain(f.period);
  const channels = useChannels(f.channel, f.period);

  // Раскрытие «Оплаты клиентов»: что именно учитывает система.
  const [payOpen, setPayOpen] = useState(false);
  const payments = usePayments(f.period, payOpen);

  return (
    <>
      <div className="card">
        <div className="card-h">
          <h3>Цепочка «реклама → деньги»</h3>
          <span className="sub">сквозная аналитика по деньгам, не по кликам</span>
        </div>
        {chain.data ? (
          <ChainView steps={chain.data} onDrill={(d) => { if (d === "payments") setPayOpen(true); }} />
        ) : chain.isError ? (
          <LoadFail query={chain} />
        ) : (
          <div style={{ padding: 30 }}><Spin /></div>
        )}
      </div>

      <PaymentsModal open={payOpen} onClose={() => setPayOpen(false)} query={payments} />


      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-h">
          <div><h3>Сводка по каналам и кампаниям</h3></div>
        </div>
        {channels.data ? (
          channels.data.length ? (
            <ChannelsTable rows={channels.data} />
          ) : (
            <EmptyState
              title="Нет данных по каналам"
              hint="Сводка по каналам собирается из расходов Яндекс Директа и выручки Битрикс24/МойСклад. Подключите источники и выполните пересчёт."
            />
          )
        ) : channels.isError ? (
          <LoadFail query={channels} />
        ) : (
          <div style={{ padding: 30 }}><Spin /></div>
        )}
      </div>
    </>
  );
}

// Окно расшифровки «Оплаты клиентов»: активный источник + список учтённых оплат.
function PaymentsModal({
  open,
  onClose,
  query,
}: {
  open: boolean;
  onClose: () => void;
  query: UseQueryResult<import("@/api/analytics").PaymentsBreakdown>;
}) {
  const d = query.data;
  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={720}
      title="Оплаты клиентов — что учитывает система"
    >
      {!d ? (
        query.isError ? (
          <div style={{ padding: 20, textAlign: "center" }}>
            <div style={{ marginBottom: 12, color: "var(--muted)" }}>Не удалось загрузить.</div>
            <Button size="small" onClick={() => query.refetch()} loading={query.isFetching}>
              Повторить
            </Button>
          </div>
        ) : (
          <div style={{ padding: 30, textAlign: "center" }}><Spin /></div>
        )
      ) : (
        <>
          <div className="pay-src">
            <div className="pay-src-h">
              Источник: <b>{d.source_label}</b>
            </div>
            <div className="pay-src-hint">{d.source_hint}</div>
            <div className="pay-src-tot">
              Учтено оплат: <b>{d.count}</b> · на сумму <b>{d.total_display}</b>
            </div>
            {!d.exact ? (
              <div className="pay-src-note">
                Демо-режим: счётчик на плашке считается по демо-модели периода, поэтому
                список может не совпадать с ним число в число. В боевом режиме — точно.
              </div>
            ) : null}
          </div>
          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            dataSource={d.items}
            pagination={d.items.length > 10 ? { pageSize: 10 } : false}
            locale={{ emptyText: "Нет учтённых оплат за период" }}
            columns={[
              { title: "Оплата / сделка", dataIndex: "name", key: "name", ellipsis: true },
              {
                title: "Менеджер", dataIndex: "mgr", key: "mgr",
                render: (v: string) => (v && v !== "—" ? v : "—"),
              },
              {
                title: "Источник", dataIndex: "src", key: "src",
                render: (v: string) => (v && v !== "—" ? <Tag>{v}</Tag> : "—"),
              },
              { title: "Дата", dataIndex: "date", key: "date", width: 108 },
              {
                title: "Сумма", dataIndex: "amount_display", key: "amount",
                align: "right" as const, width: 130,
              },
            ]}
          />
        </>
      )}
    </Modal>
  );
}
