"""Точка входа FastAPI. Все API — под префиксом /api."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("banapal.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск API :: env=%s data_source=%s", settings.app_env, settings.data_source)
    yield
    logger.info("Остановка API")


app = FastAPI(
    title="Banapal API",
    description="AI-система контроля лидов и маркетинговой аналитики",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS: в проде фронтенд и API за одним nginx (same-origin);
# для локальной разработки допускаем vite dev-сервер.
_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_url, *_dev_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"
app.include_router(health.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
