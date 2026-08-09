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
COMPOSE="docker compose -f docker-compose.prod.yml"
LIVE="/etc/letsencrypt/live/${DOMAIN}"

echo "==> 1/5 Сборка образов (первый раз занимает несколько минут, прогресс ниже)"
$COMPOSE build web api

echo "==> 2/5 Временный самоподписанный сертификат (чтобы поднять nginx)"
$COMPOSE run --rm --entrypoint "sh -c \
  'mkdir -p ${LIVE} && openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
   -keyout ${LIVE}/privkey.pem -out ${LIVE}/fullchain.pem -subj /CN=${DOMAIN}'" certbot

echo "==> 3/5 Запуск nginx"
$COMPOSE up -d web

echo "==> 4/5 Удаление временного сертификата и выпуск боевого"
$COMPOSE run --rm --entrypoint "rm -rf ${LIVE} \
  /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf" certbot
$COMPOSE run --rm --entrypoint "certbot certonly --webroot -w /var/www/certbot \
  -d ${DOMAIN} --email ${EMAIL} --agree-tos --no-eff-email --force-renewal" certbot

echo "==> 5/5 Перезагрузка nginx с боевым сертификатом"
$COMPOSE exec web nginx -s reload

echo "Готово. Сертификат выпущен для ${DOMAIN}."
echo "Теперь поднимите всю систему: docker compose -f docker-compose.prod.yml up -d --build"
