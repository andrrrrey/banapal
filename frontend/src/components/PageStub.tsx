import type { ComponentType } from "react";

// Заглушка раздела для Этапа A: каркас готов, наполнение — на Этапах B–D.
interface PageStubProps {
  Icon: ComponentType;
  title: string;
  description: string;
  stage: string;
}

export function PageStub({ Icon, title, description, stage }: PageStubProps) {
  return (
    <div className="stub">
      <div className="stub-ic">
        <Icon />
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      <span className="stage">{stage}</span>
    </div>
  );
}
