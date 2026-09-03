import { Button, Spin } from "antd";
import type { UseQueryResult } from "@tanstack/react-query";

import { useChain, useChannels } from "@/api/analytics";
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

  return (
    <>
      <div className="card">
        <div className="card-h">
          <h3>Цепочка «реклама → деньги»</h3>
          <span className="sub">сквозная аналитика по деньгам, не по кликам</span>
        </div>
        {chain.data ? (
          <ChainView steps={chain.data} />
        ) : chain.isError ? (
          <LoadFail query={chain} />
        ) : (
          <div style={{ padding: 30 }}><Spin /></div>
        )}
      </div>

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
