#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Первичный выпуск TLS-сертификата Let's Encrypt для домена из .env.
# Предусловия: A-запись DOMAIN указывает на этот VPS; порт 80 открыт;
# .env заполнен (DOMAIN, LETSENCRYPT_EMAIL). Запуск: ./scripts/init-letsencrypt.sh
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
set -a; source .env; set +a

DOMAIN="${DOMAIN:?DOMAIN не задан в .env}"
EMAIL="${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL не задан в .env}"
# По умолчанию — БЫСТРЫЙ путь: готовые образы из реестра (docker-compose.registry.yml).
# Для сборки на сервере: COMPOSE_FILE=docker-compose.prod.yml ./scripts/init-letsencrypt.sh
FILE="${COMPOSE_FILE:-docker-compose.registry.yml}"
COMPOSE="docker compose -f ${FILE}"
LIVE="/etc/letsencrypt/live/${DOMAIN}"

echo "==> 1/5 Подготовка образов (${FILE})"
# registry-режим: скачать готовые образы; build-режим: собрать. Лишнее — no-op.
$COMPOSE pull web api 2>/dev/null || true
$COMPOSE build web api 2>/dev/null || true

echo "==> 2/5 Временный самоподписанный сертификат (чтобы поднять nginx)"
$COMPOSE run --rm --entrypoint "sh -c \
  'mkdir -p ${LIVE} && openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
   -keyout ${LIVE}/privkey.pem -out ${LIVE}/fullchain.pem -subj /CN=${DOMAIN}'" certbot

echo "==> 3/5 Запуск nginx и ожидание готовности порта 80"
$COMPOSE up -d web
ready=0
for _ in $(seq 1 30); do
  if curl -sS -o /dev/null "http://localhost/.well-known/acme-challenge/ping" 2>/dev/null; then
    ready=1; break
  fi
  sleep 1
done
if [ "$ready" != "1" ]; then
  echo "ОШИБКА: nginx не отвечает на порту 80. Проверьте логи: $COMPOSE logs web"
  exit 1
fi

echo "==> 4/5 Выпуск боевого сертификата (nginx продолжает держать :80)"
$COMPOSE run --rm --entrypoint "rm -rf ${LIVE} \
  /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf" certbot
if $COMPOSE run --rm --entrypoint "certbot certonly --webroot -w /var/www/certbot \
     -d ${DOMAIN} --email ${EMAIL} --agree-tos --no-eff-email --non-interactive" certbot; then
  echo "==> 5/5 Перезагрузка nginx с боевым сертификатом"
  $COMPOSE exec web nginx -s reload
  echo "Готово. Сертификат выпущен для ${DOMAIN}."
  echo "Поднимите всю систему: docker compose up -d   (COMPOSE_FILE=${FILE})"
else
  echo "ОШИБКА выпуска сертификата. Восстанавливаю временный, чтобы nginx работал."
  $COMPOSE run --rm --entrypoint "sh -c \
    'mkdir -p ${LIVE} && openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
     -keyout ${LIVE}/privkey.pem -out ${LIVE}/fullchain.pem -subj /CN=${DOMAIN}'" certbot
  $COMPOSE restart web
  echo "Проверьте, что порт 80 открыт снаружи и DNS ${DOMAIN} → этот сервер, затем запустите скрипт снова."
  exit 1
fi
