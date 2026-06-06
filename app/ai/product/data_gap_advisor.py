"""Подсказки продавцу: какие данные загрузить для более полезного AI-анализа."""

from __future__ import annotations

from decimal import Decimal


def build_data_gap_advice(
    *,
    sku_count: int = 0,
    total_revenue: Decimal | None = None,
    margin: Decimal | None = None,
    cost_coverage_pct: Decimal | float | None = None,
    inventory_signals: bool = False,
    ad_spend_available: bool = False,
    anomalies: list[str] | None = None,
) -> list[str]:
    tips: list[str] = []

    if sku_count == 0 or total_revenue is None:
        tips.append(
            "Загрузите финансовый отчёт WB (раздел «Отчёты»), чтобы ИИ мог анализировать выручку и SKU."
        )

    cov = float(cost_coverage_pct) if cost_coverage_pct is not None else None
    if cov is None or cov < 100:
        tips.append(
            "Импортируйте себестоимость (раздел «Себестоимость») — без неё маржа и прибыль "
            "будут скрыты, рекомендации по убыточным SKU будут недоступны."
        )

    if not inventory_signals:
        tips.append(
            "Загрузите отчёт по остаткам на складе — появятся советы по slow movers и замороженному капиталу."
        )

    if not ad_spend_available:
        tips.append(
            "Добавьте отчёты по рекламным кампаниям — ИИ сможет оценивать долю рекламы в марже."
        )

    if margin is not None and margin < Decimal("15"):
        tips.append(
            "Проверьте себестоимость по топ-SKU и логистику в отчёте — маржа ниже 15% требует разбора затрат."
        )

    if anomalies:
        for msg in anomalies[:2]:
            if "себестоимость" in msg.lower() or "cost" in msg.lower():
                continue
            tips.append(f"Устраните проблему данных: {msg[:200]}")

    return tips[:5]
