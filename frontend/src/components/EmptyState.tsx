// Пустое состояние раздела: показываем, когда данных нет (обычно в боевом
// режиме до подключения соответствующей интеграции или до пересчёта).

interface EmptyStateProps {
  title?: string;
  hint?: string;
}

export function EmptyState({ title = "Пока нет данных", hint }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-ic">
        <svg fill="none" stroke="currentColor" strokeWidth={1.6} viewBox="0 0 24 24">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <path d="M3 9h18M8 4v16" strokeLinecap="round" />
        </svg>
      </div>
      <b>{title}</b>
      {hint ? <span>{hint}</span> : null}
    </div>
  );
}
