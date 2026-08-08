#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Точка входа контейнера. RUN_MODE определяет роль:
#   api    — веб-сервер FastAPI (миграции + gunicorn/uvicorn)
#   worker — планировщик APScheduler (регулярные выгрузки и пересчёт)
# ---------------------------------------------------------------------------
set -euo pipefail

RUN_MODE="${RUN_MODE:-api}"

if [ "$RUN_MODE" = "api" ]; then
  # Применяем миграции БД (на Этапе A версий ещё нет — no-op, не падает).
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head || echo "[entrypoint] миграции пропущены (нет версий)"

  # Если команда переопределена в compose (dev: uvicorn --reload) — используем её.
  if [ "$#" -gt 0 ]; then
    exec "$@"
  fi

  echo "[entrypoint] запуск gunicorn (uvicorn workers)"
  exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${WEB_CONCURRENCY:-2}" \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
elif [ "$RUN_MODE" = "worker" ]; then
  echo "[entrypoint] запуск планировщика (worker)"
  exec python -m app.worker
else
  echo "[entrypoint] неизвестный RUN_MODE=$RUN_MODE" >&2
  exit 1
fi
