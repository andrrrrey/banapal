"""Показатели дашборда: KPI, воронка, источники, таймсерии, ROMI, триаж, менеджеры, лиды."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AdCost, Baseline, Channel, Deal, KpiCard, ManagerControl, Payment, Visit
from app.services import format as f
from app.services import period as per
from app.services import romi as romi_svc


def _period_start(period: str | None, now: datetime) -> datetime:
    return per.start(period, now)


def _period_end(period: str | None, now: datetime) -> datetime | None:
    """Верхняя граница периода (исключающая); None у открытых пресетов."""
    return per.end(period, now)


def _by_deal_filters(stmt, mgr: str = "all", source: str = "all"):
    """Фильтры дашборда «менеджер» и «источник» на выборку сделок."""
    if mgr and mgr != "all":
        stmt = stmt.where(Deal.mgr == mgr)
    if source and source != "all":
        stmt = stmt.where(Deal.src == source)
    return stmt


async def _ad_totals(session: AsyncSession, period: str) -> dict[str, float]:
    """Расход/клики (Директ) и визиты (Метрика) за период из посуточного сырья.

    Рекламные показатели не разрезаются фильтрами «менеджер»/«источник»: расход
    относится к кампании, а не к ответственному, а таксономия источников Метрики
    не совпадает с SOURCE_ID Битрикс24 — смешивать их было бы неверно.

    Пока посуточного сырья нет (пересчёт не выполнялся после обновления), берём
    сохранённые итоги последнего пересчёта — иначе показатели обнулились бы.
    """
    now = datetime.now(UTC)
    start = _period_start(period, now)
    end = _period_end(period, now)
    cost_where = [AdCost.date.is_not(None), AdCost.date >= start]
    visit_where = [Visit.date.is_not(None), Visit.date >= start]
    if end is not None:
        cost_where.append(AdCost.date < end)
        visit_where.append(Visit.date < end)
    spend, clicks = (await session.execute(
        select(
            func.coalesce(func.sum(AdCost.spend), 0),
            func.coalesce(func.sum(AdCost.clicks), 0),
        ).where(*cost_where)
    )).one()
    visits = (await session.execute(
        select(func.coalesce(func.sum(Visit.visits), 0)).where(*visit_where)
    )).scalar() or 0

    has_costs = bool(await session.scalar(select(func.count()).select_from(AdCost)))
    has_visits = bool(await session.scalar(select(func.count()).select_from(Visit)))
    if has_costs and has_visits:
        return {"spend": float(spend), "clicks": float(clicks), "visits": float(visits)}

    # Резерв на данных прошлых версий: итоги каналов и базлайна за всё окно.
    legacy_spend = int((await session.execute(
        select(func.coalesce(func.sum(Channel.spend), 0))
    )).scalar() or 0)
    legacy = dict((await session.execute(
        select(Baseline.key, Baseline.value).where(Baseline.key.in_(["clicks", "visits"]))
    )).all())
    return {
        "spend": float(spend) if has_costs else float(legacy_spend),
        "clicks": float(clicks) if has_costs else float(legacy.get("clicks", 0)),
        "visits": float(visits) if has_visits else float(legacy.get("visits", 0)),
    }


def _num(value: object) -> float:
    """Терпимый парс числа (себестоимость из пользовательского поля может быть строкой)."""
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(" ", "").replace("\xa0", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


async def period_deals(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> list[Deal]:
    """Сделки дашборда за период с учётом фильтров «менеджер» и «источник»."""
    now = datetime.now(UTC)
    start = _period_start(period, now)
    end = _period_end(period, now)
    stmt = select(Deal).where(
        Deal.on_dashboard.is_(True),
        Deal.created_at.is_not(None),
        Deal.created_at >= start,
    )
    if end is not None:
        stmt = stmt.where(Deal.created_at < end)
    return list((await session.execute(
        _by_deal_filters(stmt, mgr, source)
    )).scalars().all())


def _truthy_paid(value: object) -> bool:
    """Признак «оплачено» из пользовательского поля (эквайринг Сбербанка).

    Пусто/0/нет → не оплачено; любое непустое осмысленное значение (Y, 1, дата,
    сумма, «оплачено») → оплачено."""
    if value is None:
        return False
    text = str(value).strip().lower()
    return text not in ("", "0", "n", "no", "false", "нет", "не оплачено")


def _deal_is_paid(deal: Deal, fm: dict) -> bool:
    """Оплата по сделке для источника bitrix_sber.

    Если сопоставлено поле оплаты (field_map['paid']) — берём его; иначе честно
    откатываемся к семантике выигранной стадии (как bitrix_won)."""
    col = (fm.get("fields") or {}).get("paid")
    if col:
        return _truthy_paid((deal.custom or {}).get(col))
    return deal.status_class == "st-ok"


async def _ms_payment_totals(session: AsyncSession, period: str) -> tuple[int, int]:
    """Число и сумма входящих платежей МойСклад за период (по paid_at)."""
    now = datetime.now(UTC)
    start = _period_start(period, now)
    end = _period_end(period, now)
    where = [
        Payment.source == "moysklad",
        Payment.paid_at.is_not(None),
        Payment.paid_at >= start,
    ]
    if end is not None:
        where.append(Payment.paid_at < end)
    cnt, total = (await session.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(*where)
    )).one()
    return int(cnt or 0), int(total or 0)


async def _resolve_payments_source(session: AsyncSession, override: str | None) -> str:
    """Эффективный источник оплат: явный override (фильтр экрана) или значение из БД."""
    from app.services.integrations_config import PAYMENTS_SOURCES, load_payments_source
    if override in PAYMENTS_SOURCES:
        return override  # type: ignore[return-value]
    return await load_payments_source(session)


async def _period_baseline(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all",
    payments_source: str | None = None,
) -> dict[str, float]:
    """Реальные KPI за период — по сделкам с created_at в интервале (боевой режим).

    Факт «оплаты» и «выручка» зависят от settings.payments_source (страница
    «Интеграции»):
      • bitrix_won  — выигранные сделки (status_class == 'st-ok');
      • bitrix_sber — сделки с проведённой оплатой (поле эквайринга, иначе как won);
      • moysklad    — входящие платежи МойСклад (реальные деньги; фильтр периода по
                      дате платежа).
    Маржа считается только при сопоставленном поле себестоимости (иначе 0); для
    источника moysklad маржа берётся из прибыльности МойСклад отдельно (пока 0).
    Фильтры «менеджер»/«источник» сужают выборку сделок; рекламные показатели
    (расход/клики/визиты) от них не зависят — см. _ad_totals."""
    rows = await period_deals(session, period, mgr, source)

    from app.services.integrations_config import get_field_map
    fm = await get_field_map(session)
    cost_mapped = "cost" in (fm.get("fields") or {})

    # Источник оплат: явный фильтр экрана «Сквозная аналитика» имеет приоритет,
    # иначе — значение из БД (переключение в UI действует во всех воркерах сразу).
    src = await _resolve_payments_source(session, payments_source)
    if src == "moysklad":
        # Оплаты и деньги — из реальных платежей МойСклад за период.
        pay_count, pay_sum = await _ms_payment_totals(session, period)
        payments = float(pay_count)
        revenue = float(pay_sum)
        # Маржа по деньгам МойСклад не сводится к себестоимости сделок Битрикс —
        # оставляем 0 до подключения прибыльности МойСклад (не вводим в заблуждение).
        margin = 0.0
    else:
        if src == "bitrix_sber":
            paid = [d for d in rows if _deal_is_paid(d, fm)]
        else:  # bitrix_won (по умолчанию)
            paid = [d for d in rows if d.status_class == "st-ok"]
        revenue_int = sum(int(d.amount or 0) for d in paid)
        payments = float(len(paid))
        revenue = float(revenue_int)
        if cost_mapped:
            total_cost = sum(_num((d.custom or {}).get("cost")) for d in paid)
            margin = float(int(revenue_int - total_cost))
        else:
            margin = 0.0

    # Расход/клики/визиты — из посуточного сырья источников за тот же период.
    ad = await _ad_totals(session, period)

    return {
        "leads": float(len(rows)),
        "qual": float(sum(1 for d in rows if d.stage not in (None, "Новое обращение"))),
        "deals": float(sum(1 for d in rows if (d.amount or 0) > 0)),
        "invoices": float(sum(1 for d in rows if d.invoice)),
        "payments": payments,
        "revenue": revenue,
        "margin": margin,
        "spend": ad["spend"],
        "clicks": ad["clicks"],
        "visits": ad["visits"],
        "first_contact": 0.0,
        "overdue": 0.0,
    }


async def _base_and_mult(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all",
    payments_source: str | None = None,
) -> tuple[dict[str, float], float]:
    """Базлайн и множитель: боевой режим — реальная фильтрация по датам (mult=1),
    демо — сохранённый сид × коэффициент периода (как в прототипе).

    payments_source — необязательный override источника оплат (фильтр экрана
    «Сквозная аналитика»); действует только в боевом режиме."""
    if settings.data_source == "real":
        return await _period_baseline(session, period, mgr, source, payments_source), 1.0
    return await _baselines(session), per.mult(period)


async def _baselines(session: AsyncSession) -> dict[str, float]:
    rows = (await session.execute(select(Baseline))).scalars().all()
    return {b.key: b.value for b in rows}


def _minutes(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} мин"


async def kpis(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> list[dict]:
    base, m = await _base_and_mult(session, period, mgr, source)
    cards = (await session.execute(select(KpiCard).order_by(KpiCard.position))).scalars().all()
    # В боевом режиме демо-дельты и спарклайны из сида не показываем — только
    # реальные значения (тренд формируется на этапе накопления истории).
    real = settings.data_source == "real"
    # Каналы нужны для реального ROMI (карта с static_value в прототипе — «+197%»),
    # и считаются за выбранный период — иначе ROMI не отвечает на переключатель.
    channels_rows = await _period_channels(session, period, mgr, source) if real else []

    out: list[dict] = []
    for c in cards:
        value: float | None = None
        if c.static_value is not None:
            if real:
                # Не показываем демо-строку: считаем ROMI из каналов, иначе «—».
                r = romi_svc.romi(
                    sum(int(ch["margin"] or 0) for ch in channels_rows),
                    sum(int(ch["spend"] or 0) for ch in channels_rows),
                ) if c.key == "romi" else None
                display = f"{r:+d}%" if r is not None else "—"
            else:
                display = c.static_value
        else:
            raw = (base.get(c.base_key or "", 0)) * (m if c.scales else 1)
            value = raw
            if c.kind == "money":
                display = f.money_short(raw)
            elif c.kind == "minutes":
                display = _minutes(raw)
            else:
                display = f.fmt(raw)
        out.append({
            "key": c.key, "label": c.label, "icon": c.icon, "svg": c.svg, "kind": c.kind,
            "value": value, "display": display,
            "trend": "flat" if real else c.trend,
            "delta": "" if real else c.delta,
            "spark": [] if real else c.spark,
            "drill": c.drill, "period_label": per.label(period),
        })
    return out


async def filter_options(session: AsyncSession) -> dict:
    """Реальные значения для фильтров (менеджеры/каналы/источники) из данных БД.

    Список строится по тем же сделкам, которые реально считают карточки и таблицы:
    только сделки дашборда (``on_dashboard``), а в боевом режиме — ещё и с
    распознанной датой создания (``created_at``). Иначе в фильтре появлялись
    менеджеры и источники (например SOURCE_ID «cpc»), у которых нет ни одной
    учитываемой сделки: выбор такого значения обнулял все витрины при любом периоде,
    и это выглядело как «фильтр не работает». Теперь любой источник из списка при
    каком-то периоде показывает данные, а «пустые» значения справочника не
    предлагаются вовсе."""
    # Базовый предикат «сделка учитывается витринами» — совпадает с period_deals.
    countable = [Deal.on_dashboard.is_(True)]
    if settings.data_source == "real":
        countable.append(Deal.created_at.is_not(None))

    mgrs = (await session.execute(
        select(Deal.mgr)
        .where(*countable, Deal.mgr.is_not(None), Deal.mgr != "—")
        .distinct()
    )).scalars().all()
    chans = (await session.execute(
        select(Channel.name).order_by(Channel.position)
    )).scalars().all()
    srcs = (await session.execute(
        select(Deal.src)
        .where(*countable, Deal.src.is_not(None), Deal.src != "—")
        .distinct()
    )).scalars().all()
    return {
        "managers": sorted({m for m in mgrs if m}),
        "channels": list(chans),
        "sources": sorted({s for s in srcs if s}),
    }


async def funnel(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> list[dict]:
    base, m = await _base_and_mult(session, period, mgr, source)
    stages = [
        ("leads", "Лиды"), ("qual", "Квалификация"), ("deals", "Сделки"),
        ("invoices", "Счета"), ("payments", "Оплаты"),
    ]
    return [{"label": label, "value": round(base.get(key, 0) * m)} for key, label in stages]


# Палитра для источников лидов (SOURCE_ID Битрикс24 — произвольный справочник).
_SOURCE_COLORS = ["#635BFF", "#9E77ED", "#1BA9C7", "#12B76A", "#F79009", "#F04438", "#8E96AD"]


async def sources(
    session: AsyncSession, period: str = per.DEFAULT_PERIOD,
    mgr: str = "all", source: str = "all",
) -> list[dict]:
    """Источники лидов за период.

    В боевом режиме считаем по источнику сделки (SOURCE_ID Битрикс24): так
    диаграмма охватывает все сделки, отвечает на переключатель периода и на
    фильтры дашборда. В демо — сохранённые каналы прототипа."""
    if settings.data_source != "real":
        chs = (await session.execute(select(Channel).order_by(Channel.position))).scalars().all()
        return [
            {"name": c.name, "short_name": f.short_channel(c.name),
             "color": c.color, "leads": c.leads}
            for c in chs
        ]

    deals = await period_deals(session, period, mgr, source)
    counts: dict[str, int] = {}
    for d in deals:
        counts[d.src or "—"] = counts.get(d.src or "—", 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [
        {"name": name, "short_name": f.short_channel(name),
         "color": _SOURCE_COLORS[i % len(_SOURCE_COLORS)], "leads": n}
        for i, (name, n) in enumerate(ordered)
    ]


async def revenue_series(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> dict:
    base, m = await _base_and_mult(session, period, mgr, source)
    days = ["09", "11", "13", "15", "17"] if per.norm_period(period) == "today" \
        else ["1", "5", "10", "15", "20", "25", "30"]
    total_rev = base.get("revenue", 0) * m
    total_margin = base.get("margin", 0) * m
    if settings.data_source == "real":
        # Посуточной истории пока нет — показываем ровное распределение реального
        # итога, без придуманной кривой роста и синтетической маржи (как в демо).
        revenue = [round(total_rev / len(days))] * len(days)
        margin = [round(total_margin / len(days))] * len(days)
    else:
        per_day = total_rev / len(days)
        revenue = [round(per_day * (0.7 + i * 0.09)) for i in range(len(days))]
        margin = [round(v * 0.34) for v in revenue]
    return {"days": days, "revenue": revenue, "margin": margin}


async def _period_channels(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> list[dict]:
    """Каналы за период (посуточное сырьё) либо сохранённые строки как резерв."""
    from app.services import channels as ch_svc

    rebuilt = (
        await ch_svc.for_period(session, period, mgr=mgr, source=source)
        if settings.data_source == "real" else None
    )
    if rebuilt is not None:
        return rebuilt
    rows = (await session.execute(select(Channel).order_by(Channel.position))).scalars().all()
    return [
        {"name": c.name, "color": c.color, "spend": c.spend, "leads": c.leads,
         "deals": c.deals, "payments": c.payments, "revenue": c.revenue, "margin": c.margin}
        for c in rows
    ]


async def romi_by_channel(
    session: AsyncSession, period: str = per.DEFAULT_PERIOD,
    mgr: str = "all", source: str = "all",
) -> list[dict]:
    chs = await _period_channels(session, period, mgr, source)
    out = []
    for c in chs:
        r = f.romi_of(c["spend"], c["margin"])
        if r is not None:
            out.append({"name": c["name"], "short_name": f.short_channel(c["name"]), "romi": r})
    return out


async def attention(session: AsyncSession, mgr: str = "all", source: str = "all") -> dict:
    """Блок «Что требует внимания сейчас».

    Период не применяется намеренно (блок показывает состояние на текущий момент),
    но фильтры «менеджер»/«источник» сужают выборку — иначе они не действовали бы
    на самую заметную часть дашборда."""
    from app.services import violations as vio
    from app.services.integrations_config import get_recompute_status

    res = await vio.evaluate_current(session, mgr=mgr, source=source)
    regular = res["regular"]
    review = res["review"]
    cap = await vio.risk_amount_cap(session)
    money_at_risk = vio.money_at_risk(regular, cap)
    risk_stmt = select(Deal).where(Deal.risk.is_not(None), Deal.on_dashboard.is_(True))
    risk_leads = (await session.execute(
        _by_deal_filters(risk_stmt, mgr, source)
    )).scalars().all()

    # Реальные счётчики и суммы по типам нарушений (сумма — с дедупом и фильтром выбросов).
    def _count(ptype: str) -> int:
        return sum(1 for v in regular if v.get("ptype") == ptype)

    def _money(ptype: str) -> int:
        by_deal: dict[str, int] = {}
        for v in regular:
            if v.get("ptype") == ptype and v.get("severity") == "over":
                amount = int(v.get("amount") or 0)
                if cap and amount > cap:
                    continue
                by_deal[str(v.get("ref") or v.get("name"))] = amount
        return sum(by_deal.values())

    # Число источников с ошибкой/пропуском в последнем пересчёте.
    rc = await get_recompute_status(session)
    src_errors = sum(1 for s in (rc.get("sources") or {}).values()
                     if s.get("status") in ("error", "skipped"))

    tiles = [
        {"n": _count("overdue_contact"), "label": "Просроченные лиды",
         "sub": "первый контакт > норматива",
         "cls": "red", "icon": "clock", "drill": "monitor:overdue_contact"},
        {"n": _count("no_task"), "label": "Сделки без задач",
         "sub": f"{f.money(_money('no_task'))} под риском",
         "cls": "amber", "icon": "task", "drill": "monitor:no_task"},
        {"n": _count("stuck"), "label": "Сделки без движения",
         "sub": f"{f.money(_money('stuck'))} под риском",
         "cls": "red", "icon": "freeze", "drill": "monitor:stuck"},
        {"n": _count("no_recontact"), "label": "Без повторного касания",
         "sub": f"{f.money(_money('no_recontact'))} под риском",
         "cls": "amber", "icon": "touch", "drill": "monitor:no_recontact"},
        {"n": len(review), "label": "Отказы / спам на проверке",
         "sub": "оценочные нарушения",
         "cls": "violet", "icon": "flag", "drill": "monitor:spam"},
        {"n": _count("fields"), "label": "Не заполнены поля",
         "sub": "обязательные поля сделки",
         "cls": "amber", "icon": "romi", "drill": "monitor:fields"},
        {"n": src_errors, "label": "Ошибки источников данных",
         "sub": "проверьте интеграции",
         "cls": "gray", "icon": "plug", "drill": "data"},
    ]
    return {
        "money_at_risk": money_at_risk,
        "money_at_risk_display": f.money(money_at_risk),
        "risk_leads": len(risk_leads),
        "tiles": tiles,
    }


def _manager_zone(overdue: int, notask: int) -> tuple[str, str]:
    """Зона менеджера по числу просрочек/сделок без задачи."""
    if overdue >= 2 or notask >= 2:
        return "зона риска", "t-red"
    if overdue >= 1 or notask >= 1:
        return "наблюдение", "t-amber"
    return "в норме", "t-green"


async def _managers_from_deals(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all"
) -> list[dict]:
    """Агрегаты по менеджерам из реальных сделок Битрикс24 (боевой режим).

    Имя менеджера уже сопоставлено при выгрузке (ASSIGNED_BY_ID → ФИО через
    справочник сотрудников). Выборка ограничена периодом и фильтрами дашборда.
    Просрочки и «сделки без задачи» берём из движка регламента (те же нарушения,
    что на «Мониторинге»)."""
    now = datetime.now(UTC)
    start = _period_start(period, now)
    end = _period_end(period, now)
    stmt = select(Deal).where(
        Deal.on_dashboard.is_(True), Deal.mgr.is_not(None), Deal.mgr != "—",
        Deal.created_at.is_not(None), Deal.created_at >= start,
    )
    if end is not None:
        stmt = stmt.where(Deal.created_at < end)
    deals = (await session.execute(_by_deal_filters(stmt, mgr, source))).scalars().all()
    if not deals:
        return []

    # Нарушения по менеджерам: просрочки (over) и «нет задачи» (ptype no_task).
    from app.services import violations as vio
    evaluated = await vio.evaluate_current(session, mgr=mgr, source=source)
    overdue: dict[str, int] = {}
    notask: dict[str, int] = {}
    for v in evaluated.get("regular", []):
        name = v.get("mgr")
        if not name:
            continue
        if v.get("over"):
            overdue[name] = overdue.get(name, 0) + 1
        if v.get("ptype") == "no_task":
            notask[name] = notask.get(name, 0) + 1

    agg: dict[str, dict] = {}
    for d in deals:
        m = agg.setdefault(d.mgr, {
            "name": d.mgr, "inwork": 0, "invoices": 0, "payments": 0, "paysum": 0,
        })
        if d.status_class == "st-mid":  # в работе (не выиграна и не проиграна)
            m["inwork"] += 1
        if d.invoice:
            m["invoices"] += 1
        if d.status_class == "st-ok":  # выигранная сделка
            m["payments"] += 1
            m["paysum"] += int(d.amount or 0)

    out: list[dict] = []
    for m in agg.values():
        ov, nt = overdue.get(m["name"], 0), notask.get(m["name"], 0)
        zone_label, zone_class = _manager_zone(ov, nt)
        out.append({
            **m, "overdue": ov, "notask": nt, "fc": "—",
            "paysum_display": f.money(m["paysum"]),
            "zone_label": zone_label, "zone_class": zone_class,
        })
    # Самые результативные — выше; при равенстве по имени.
    out.sort(key=lambda x: (-x["paysum"], x["name"]))
    return out


async def managers(
    session: AsyncSession, period: str = per.DEFAULT_PERIOD,
    mgr: str = "all", source: str = "all",
) -> list[dict]:
    if settings.data_source == "real":
        return await _managers_from_deals(session, period, mgr, source)
    rows = (await session.execute(
        select(ManagerControl).order_by(ManagerControl.position)
    )).scalars().all()
    return [
        {
            "name": m.name, "inwork": m.inwork, "overdue": m.overdue, "notask": m.notask,
            "fc": m.fc, "invoices": m.invoices, "payments": m.payments,
            "paysum": m.paysum, "paysum_display": f.money(m.paysum),
            "zone_label": m.zone_label, "zone_class": m.zone_class,
        }
        for m in rows
    ]


# Подписи источников оплат для раскрытия «Оплаты клиентов» на сквозной аналитике.
_PAYMENTS_LABELS = {
    "bitrix_won": (
        "Выигранные сделки Битрикс24",
        "«Оплатой» считается сделка на успешной стадии воронки (семантика «успех»).",
    ),
    "moysklad": (
        "Входящие платежи МойСклад",
        "«Оплатой» считается входящий платёж в МойСклад — реальные деньги на счёте/кассе.",
    ),
    "bitrix_sber": (
        "Оплата в сделке (эквайринг Сбербанка)",
        "«Оплатой» считается сделка с проведённой оплатой (по полю эквайринга; "
        "без сопоставленного поля — по успешной стадии).",
    ),
}


async def payments_breakdown(
    session: AsyncSession, period: str, mgr: str = "all", source: str = "all",
    payments_source: str | None = None,
) -> dict:
    """Расшифровка «Оплаты клиентов»: какие именно оплаты учтены за период.

    Прозрачность для сквозной аналитики: показывает активный источник оплат и сам
    список учтённых оплат (сделки Битрикс или платежи МойСклад). payments_source —
    override источника (фильтр экрана), иначе берётся значение из БД."""
    from app.services.integrations_config import get_field_map
    src = await _resolve_payments_source(session, payments_source)
    label, hint = _PAYMENTS_LABELS.get(src, _PAYMENTS_LABELS["bitrix_won"])
    real = settings.data_source == "real"

    items: list[dict] = []
    if src == "moysklad":
        now = datetime.now(UTC)
        start = _period_start(period, now)
        end = _period_end(period, now)
        where = [
            Payment.source == "moysklad",
            Payment.paid_at.is_not(None),
            Payment.paid_at >= start,
        ]
        if end is not None:
            where.append(Payment.paid_at < end)
        pays = (await session.execute(
            select(Payment).where(*where).order_by(Payment.paid_at.desc())
        )).scalars().all()
        for p in pays:
            items.append({
                "name": "Входящий платёж",
                "mgr": "", "src": "МойСклад",
                "date": p.paid_at.strftime("%d.%m.%Y") if p.paid_at else "—",
                "amount": int(p.amount or 0),
                "amount_display": f.money(p.amount) if p.amount else "—",
            })
    else:
        # Сделки за период (боевой режим) или все сделки дашборда (демо).
        if real:
            deals = await period_deals(session, period, mgr, source)
        else:
            stmt = _by_deal_filters(
                select(Deal).where(Deal.on_dashboard.is_(True)).order_by(Deal.position),
                mgr, source,
            )
            deals = list((await session.execute(stmt)).scalars().all())
        fm = await get_field_map(session)
        for d in deals:
            paid = _deal_is_paid(d, fm) if src == "bitrix_sber" else d.status_class == "st-ok"
            if not paid:
                continue
            when = d.created_at.strftime("%d.%m.%Y") if d.created_at else (d.first_contact or "—")
            items.append({
                "name": d.name, "mgr": d.mgr or "—", "src": d.src or "—",
                "date": when,
                "amount": int(d.amount or 0),
                "amount_display": f.money(d.amount) if d.amount else "—",
            })

    total = sum(i["amount"] for i in items)
    return {
        "source": src,
        "source_label": label,
        "source_hint": hint,
        # В демо число оплат = сид × коэффициент периода, поэтому список может не
        # совпадать со счётчиком плашки — помечаем, чтобы не вводить в заблуждение.
        "exact": real or src == "moysklad",
        "count": len(items),
        "total": total,
        "total_display": f.money(total) if total else "0 ₽",
        "items": items,
    }


async def leads(
    session: AsyncSession, mgr: str = "all", source: str = "all",
    risk: str | None = None, period: str = "30",
) -> list[dict]:
    stmt = select(Deal).where(Deal.on_dashboard.is_(True))
    # В боевом режиме список лидов следует выбранному периоду (по дате создания),
    # чтобы переключатель периода менял и таблицу «Обработка лидов».
    if settings.data_source == "real":
        now = datetime.now(UTC)
        start = _period_start(period, now)
        end = _period_end(period, now)
        stmt = stmt.where(Deal.created_at.is_not(None), Deal.created_at >= start)
        if end is not None:
            stmt = stmt.where(Deal.created_at < end)
    stmt = _by_deal_filters(stmt, mgr, source)
    if risk == "risk":
        stmt = stmt.where(Deal.risk.is_not(None))
    stmt = stmt.order_by(Deal.position)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "name": d.name, "src": d.src, "mgr": d.mgr,
            "status_label": d.status_label, "status_class": d.status_class,
            "fc": d.first_contact, "call": d.call, "inv": d.invoice, "pay": d.paid,
            "amount": d.amount, "amount_display": f.money(d.amount) if d.amount else "—",
            "risk": d.risk, "tags": d.tags, "ai": d.ai_comment, "reason": d.refuse_reason,
        }
        for d in rows
    ]
