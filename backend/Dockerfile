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
# Шаг устойчив к недоступности источника при сборке (можно доустановить позже).
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*; \
    if curl -fsSL https://gu-st.ru/content/Other/doc/russiantrustedca.pem \
         -o /usr/local/share/ca-certificates/russian-trusted-ca.crt; then \
      update-ca-certificates; \
      cat /usr/local/share/ca-certificates/russian-trusted-ca.crt \
        >> "$(python -c 'import certifi; print(certifi.where())')"; \
    else \
      echo "WARN: не удалось скачать Russian Trusted CA — доустановите вручную (docs/DEPLOYMENT.md)"; \
    fi

# Исходный код
COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
