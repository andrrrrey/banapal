# syntax=docker/dockerfile:1

# --- Стадия сборки зависимостей (компиляторы только здесь) ---
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
# Кэш pip ускоряет повторные сборки; зависимости ставятся в префикс /install.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && pip install --prefix=/install .

# --- Финальный образ (без компиляторов → меньше размер и быстрее экспорт) ---
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установленные зависимости из стадии сборки
COPY --from=builder /install /usr/local

# Корневой и выпускающий сертификаты НУЦ Минцифры (Russian Trusted CA).
# По умолчанию ОТКЛЮЧЕНО: интеграции Этапа 1 (Битрикс24, Яндекс, Calltouch,
# МойСклад) используют обычные коммерческие сертификаты. CA нужен только для
# прямых API российских банков/платёжных шлюзов (вне объёма Этапа 1) — включить:
#   docker compose ... build --build-arg RUSSIAN_CA=on api
# либо доустановить в рантайме (docs/ADMIN.md). Это экономит время сборки.
ARG RUSSIAN_CA=off
RUN set -eux; \
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
