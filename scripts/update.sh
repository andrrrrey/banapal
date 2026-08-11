#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Лёгкое применение обновлений кода — БЕЗ пересоздания TLS-сертификата.
#
# Что делает:
#   1) забирает свежие образы (registry) или пересобирает (build-режим);
#   2) перезапускает изменившиеся контейнеры (api применит миграции БД сам);
#   3) чистит устаревшие образы, чтобы не забивать диск.
# Сертификат Let's Encrypt НЕ трогается (продлевается автоматически сервисом
# certbot). Именно этот скрипт нужно запускать после каждого обновления кода.
#
# Использование:
#   ./scripts/update.sh
#   COMPOSE_FILE=docker-compose.prod.yml ./scripts/update.sh   # сборка на сервере
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
set -a; source .env; set +a

FILE="${COMPOSE_FILE:-docker-compose.registry.yml}"
COMPOSE="docker compose -f ${FILE}"

echo "==> 1/3 Получение свежих образов (${FILE})"
# registry-режим: pull готовых образов; build-режим: сборка. Неприменимое — no-op.
$COMPOSE pull 2>/dev/null || true
$COMPOSE build 2>/dev/null || true

echo "==> 2/3 Перезапуск сервисов (миграции БД применит api при старте)"
$COMPOSE up -d

echo "==> 3/3 Очистка устаревших образов"
docker image prune -f >/dev/null 2>&1 || true

echo "✓ Обновление применено. TLS-сертификат не затронут."
echo "  Логи API:    $COMPOSE logs -f api"
echo "  Статус:      $COMPOSE ps"
