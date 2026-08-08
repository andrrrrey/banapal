import { PageStub } from "@/components/PageStub";
import { DashboardIcon } from "@/layout/icons";

export default function DashboardPage() {
  return (
    <PageStub
      Icon={DashboardIcon}
      title="Дашборд"
      description="KPI, блок «Что требует внимания», воронка обработки, источники лидов, выручка и маржа, ROMI по каналам, контроль по менеджерам и таблица лидов."
      stage="Наполнение — Этап D"
    />
  );
}
