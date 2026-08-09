# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости (сборка asyncpg и т.п.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей по pyproject (кэшируемый слой)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Корневой и выпускающий сертификаты НУЦ Минцифры (Russian Trusted CA) —
# нужны для работы с API российских банков и сервисов (раздел 7.2 ТЗ).
# Добавляются и в системное хранилище, и в бандл certifi (его использует httpx).
# Шаг НЕ должен блокировать сборку: строгие таймауты curl + проверка PEM;
# при недоступности источника сборка продолжается (можно доустановить позже,
# см. docs/ADMIN.md). Отключить попытку загрузки: --build-arg RUSSIAN_CA=off
ARG RUSSIAN_CA=on
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*; \
    if [ "$RUSSIAN_CA" = "on" ] \
       && curl -fsSL --connect-timeout 10 --max-time 60 --retry 2 \
            https://gu-st.ru/content/Other/doc/russiantrustedca.pem -o /tmp/rt.pem \
       && grep -q "BEGIN CERTIFICATE" /tmp/rt.pem; then \
      cp /tmp/rt.pem /usr/local/share/ca-certificates/russian-trusted-ca.crt; \
      update-ca-certificates; \
      cat /tmp/rt.pem >> "$(python -c 'import certifi; print(certifi.where())')"; \
      echo "Russian Trusted CA установлен"; \
    else \
      echo "WARN: Russian Trusted CA не установлен при сборке — доустановите вручную (docs/ADMIN.md)"; \
    fi

# Исходный код
COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
