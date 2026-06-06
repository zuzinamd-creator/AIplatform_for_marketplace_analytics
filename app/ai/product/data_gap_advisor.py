"""Подсказки продавцу: какие данные загрузить для более полезного AI-анализа."""

from __future__ import annotations

from decimal import Decimal


def build_data_gap_advice(
    *,
    sku_count: int = 0,
    total_revenue: Decimal | None = None,
    margin: Decimal | None = None,
    total_profit: Decimal | None = None,
    cost_coverage_pct: Decimal | float | None = None,
    cost_data_available: bool = False,
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
    has_profit_signal = margin is not None or (total_profit is not None and total_profit > 0)
    if cost_data_available or (cov is not None and cov >= 100) or (has_profit_signal and cov is None):
        pass
    elif cov is not None and cov >= 80:
        tips.append(
            f"Себестоимость покрывает {cov:.0f}% SKU с продажами — добавьте cost для оставшихся "
            "артикулов, чтобы ИИ нашёл убыточные позиции."
        )
    elif cov is not None and cov > 0:
        tips.append(
            f"Себестоимость загружена частично ({cov:.0f}% SKU) — дополните cost по артикулам "
            "из отчёта о продажах для анализа маржи по SKU."
        )
    elif not has_profit_signal:
        tips.append(
            "Импортируйте себестоимость (раздел «Себестоимость») — без неё маржа и прибыль "
            "скрыты, рекомендации по убыточным SKU недоступны."
        )

    if not inventory_signals:
        tips.append(
            "Загрузите отчёт по остаткам на складе — появятся советы по slow movers и замороженному капиталу."
        )

    if not ad_spend_available:
        tips.append(
            "Добавьте отчёты по рекламным кампаниям — ИИ сможет оценивать долю рекламы в марже."
        )

    if margin is not None and margin < Decimal("15") and has_profit_signal:
        tips.append(
            "Маржа ниже 15% — проверьте топ-SKU с высокой логистикой или комиссией в детализации."
        )

    if anomalies:
        for msg in anomalies[:2]:
            low = msg.lower()
            if "себестоимость" in low and has_profit_signal:
                continue
            tips.append(f"Устраните проблему данных: {msg[:200]}")

    return tips[:5]
