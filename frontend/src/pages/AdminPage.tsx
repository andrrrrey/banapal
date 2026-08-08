import { PageStub } from "@/components/PageStub";
import { AdminIcon } from "@/layout/icons";

export default function AdminPage() {
  return (
    <PageStub
      Icon={AdminIcon}
      title="Админ-панель регламента"
      description="Пороги по этапам, правила по задачам, обязательные поля, рабочий график и календарь, логика создания задач, правило дублей и история изменений с откатом."
      stage="Наполнение — Этап C"
    />
  );
}
