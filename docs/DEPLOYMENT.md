# Развёртывание Banapal на VPS (домен banapal.futuguru.com)

Пошаговая инструкция запуска системы на сервере с HTTPS. Занимает ~20–30 минут.

## 0. Что потребуется
- VPS: Ubuntu 22.04/24.04 LTS, 2–4 vCPU, 8 ГБ RAM, 60–80 ГБ SSD, root/SSH-доступ.
- Домен **banapal.futuguru.com** с доступом к DNS-настройкам.
- Ключи API интеграций — см. [INTEGRATIONS.md](INTEGRATIONS.md) (можно заполнить позже: система стартует на демо-данных).

## 1. DNS: направить домен на сервер
В панели управления доменом futuguru.com создайте **A-запись**:

```
banapal.futuguru.com.   A   <IP_вашего_VPS>
```

Проверьте распространение (с локальной машины):
```bash
dig +short banapal.futuguru.com   # должен вернуть IP вашего VPS
```
TLS-сертификат не выпустится, пока запись не указывает на сервер.

## 2. Подготовка сервера
Подключитесь по SSH и установите Docker:
```bash
ssh root@<IP_вашего_VPS>

# Docker + Compose plugin
curl -fsSL https://get.docker.com | sh
docker compose version   # проверка

# Открыть порты (если включён firewall)
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

## 3. Получить код
```bash
git clone <URL_репозитория> /opt/banapal
cd /opt/banapal
git checkout claude/banapal-development-plan-9l0g7v   # ветка разработки
```

## 4. Настроить окружение (.env)
```bash
cp .env.example .env
nano .env
```
Заполните минимум:
- `DOMAIN=banapal.futuguru.com`, `PUBLIC_URL=https://banapal.futuguru.com`
- `LETSENCRYPT_EMAIL=<ваш e-mail>`
- `POSTGRES_PASSWORD`, `ADMIN_LOGIN`, `ADMIN_PASSWORD` — задайте надёжные значения
- `SESSION_SECRET` — сгенерируйте: `openssl rand -hex 32`
- `DATA_SOURCE=mock` (пока нет доступов) либо `real` (когда заполните интеграции)

Куда вносить ключи API каждой интеграции — подробно в [INTEGRATIONS.md](INTEGRATIONS.md).
Все секреты хранятся только в `.env` (в репозиторий не попадают).

## 5. Выпустить TLS-сертификат (Let's Encrypt)
```bash
./scripts/init-letsencrypt.sh
```
Скрипт поднимет временный nginx, пройдёт проверку домена и выпустит боевой
сертификат. Требует, чтобы DNS (шаг 1) уже указывал на сервер и порт 80 был открыт.

## 6. Запустить систему
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Поднимутся: `db` (PostgreSQL 16), `api` (FastAPI, миграции применяются автоматически),
`worker` (планировщик), `web` (nginx + собранный фронтенд, HTTPS), `certbot` (автопродление).

Откройте **https://banapal.futuguru.com** → страница входа → логин/пароль из `.env`.

## 7. Переключение на боевые данные
1. Заполните доступы интеграций в `.env` (см. [INTEGRATIONS.md](INTEGRATIONS.md)).
2. Установите `DATA_SOURCE=real`.
3. Перезапустите и выполните первичную выгрузку:
```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api python -m app.services.ingest
```
Далее выгрузка и пересчёт идут по расписанию (планировщик `worker`).

## 8. Резервное копирование
Ручной бэкап БД:
```bash
./scripts/backup_db.sh          # создаст backups/banapal_<дата>.sql.gz
```
Автоматически (ежедневно в 03:00) — добавьте в crontab:
```bash
crontab -e
# 0 3 * * * cd /opt/banapal && ./scripts/backup_db.sh >> /var/log/banapal-backup.log 2>&1
```

## Проверка и обслуживание
- Логи: `docker compose -f docker-compose.prod.yml logs -f api worker web`
- Статус: `docker compose -f docker-compose.prod.yml ps`
- Обновление кода: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
- Подробнее — [ADMIN.md](ADMIN.md).

## Частые вопросы
- **Сертификат не выпустился** — проверьте `dig +short banapal.futuguru.com` (должен быть IP VPS) и что порт 80 открыт.
- **Не скачался Russian Trusted CA при сборке** (нужен для API росс. сервисов) — см. раздел «Russian Trusted CA» в [ADMIN.md](ADMIN.md).
- **502 на /api** — контейнер `api` ещё стартует (миграции); подождите и проверьте логи.
