import { PageStub } from "@/components/PageStub";
import { AiIcon } from "@/layout/icons";

export default function AiPage() {
  return (
    <PageStub
      Icon={AiIcon}
      title="AI-инсайты"
      description="Интерпретация показателей: закономерности, отклонения и риски, не видимые из обычной статистики. Вызовы модели — по расписанию, на слое интерпретации."
      stage="Наполнение — Этап D"
    />
  );
}
