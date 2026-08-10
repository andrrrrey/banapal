"""ORM-модели. Импорт здесь регистрирует таблицы в Base.metadata (Alembic, create_all)."""

from app.models.analytics import (
    AiInsight,
    Baseline,
    BudgetRec,
    KpiCard,
    MinusWord,
)
from app.models.crm import Deal, ManagerControl, StageHistory, Task, Violation
from app.models.marketing import (
    AdCost,
    Call,
    Campaign,
    Channel,
    Payment,
    Product,
    Visit,
)
from app.models.settings import IntegrationSettings, RegulationConfig, SettingsHistory

__all__ = [
    "AdCost",
    "AiInsight",
    "Baseline",
    "BudgetRec",
    "Call",
    "Campaign",
    "Channel",
    "Deal",
    "IntegrationSettings",
    "KpiCard",
    "ManagerControl",
    "MinusWord",
    "Payment",
    "Product",
    "RegulationConfig",
    "SettingsHistory",
    "StageHistory",
    "Task",
    "Violation",
    "Visit",
]
