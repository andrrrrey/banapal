import { PageStub } from "@/components/PageStub";
import { AnalyticsIcon } from "@/layout/icons";

export default function AnalyticsPage() {
  return (
    <PageStub
      Icon={AnalyticsIcon}
      title="Сквозная аналитика"
      description="Цепочка «реклама → визит → звонок → сделка → оплата → маржа»: сводка по каналам и кампаниям с детализацией до конкретных сделок."
      stage="Наполнение — Этап D"
    />
  );
}
