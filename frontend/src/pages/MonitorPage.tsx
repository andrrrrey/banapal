import { PageStub } from "@/components/PageStub";
import { MonitorIcon } from "@/layout/icons";

export default function MonitorPage() {
  return (
    <PageStub
      Icon={MonitorIcon}
      title="Мониторинг Битрикс24"
      description="Нарушения регламента в реальном времени, статистика по типам и блок «Требует решения руководителя» (оценочные нарушения без автоклассификации)."
      stage="Наполнение — Этап C"
    />
  );
}
