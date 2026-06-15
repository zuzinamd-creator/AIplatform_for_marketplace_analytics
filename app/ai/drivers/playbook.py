"""Deterministic playbook: check / action / effect per driver type (no LLM)."""

from __future__ import annotations

from decimal import Decimal

from app.ai.drivers.sku_factors import DominantFactor, FactorDeltas

CAUSE_CONFIDENCE_SCORE = {
    "confirmed": 0.90,
    "probable": 0.65,
    "check_only": 0.35,
}

_DRIVER_LABELS = {
    "commission": "комиссия WB",
    "logistics": "логистика",
    "returns": "возвраты",
    "price": "снижение цены",
    "volume": "снижение объёма продаж",
}


def estimate_effect(driver_type: str, factor_delta: Decimal, *, static_amount: Decimal | None = None) -> tuple[int, int]:
    base = abs(factor_delta) if factor_delta else (static_amount or Decimal("0"))
    if base <= 0:
        return 0, 0
    if driver_type in ("commission", "logistics", "returns"):
        low = int((base * Decimal("0.20")).quantize(Decimal("1")))
        high = int((base * Decimal("0.35")).quantize(Decimal("1")))
        return low, high
    if driver_type == "price":
        low = int((base * Decimal("0.15")).quantize(Decimal("1")))
        high = int((base * Decimal("0.30")).quantize(Decimal("1")))
        return low, high
    if driver_type == "volume":
        low = int((base * Decimal("500")).quantize(Decimal("1")))
        high = int((base * Decimal("1200")).quantize(Decimal("1")))
        return low, high
    return 0, 0


def build_cause_text(
    driver_type: str,
    factors: FactorDeltas | None,
    dominant: DominantFactor,
) -> str:
    label = _DRIVER_LABELS.get(driver_type, driver_type)
    delta = dominant.factor_delta
    if driver_type == "commission" and factors:
        return f"Комиссия WB выросла на +{delta:.0f} ₽ по SKU."
    if driver_type == "logistics" and factors:
        return f"Логистика выросла на +{delta:.0f} ₽ по SKU."
    if driver_type == "returns" and factors:
        return f"Возвраты выросли на +{delta:.0f} ₽ по SKU."
    if driver_type == "price" and factors and factors.price_a is not None and factors.price_b is not None:
        return f"Средняя цена снизилась: {factors.price_b:.0f} → {factors.price_a:.0f} ₽/шт."
    if driver_type == "volume" and factors:
        return f"Объём продаж SKU изменился на {factors.units_delta:+d} шт."
    if driver_type == "logistics":
        return f"Высокая доля логистики от выручки SKU ({delta:.0f} ₽)."
    if driver_type == "commission":
        return f"Высокая доля комиссии WB от выручки SKU ({delta:.0f} ₽)."
    if driver_type == "returns":
        return f"Высокая сумма возвратов по SKU ({delta:.0f} ₽)."
    return f"Основной фактор — {label}."


def playbook_checks(driver_type: str) -> list[str]:
    mapping = {
        "commission": [
            "Проверьте участие SKU в акциях WB",
            "Сверьте цену до и после СПП в кабинете",
            "Проверьте ставку комиссии в финансовом отчёте за период",
        ],
        "logistics": [
            "Проверьте габариты и вес в карточке WB",
            "Сверьте фактическую упаковку с указанной в карточке",
            "Проверьте тариф логистики в отчёте за период",
        ],
        "returns": [
            "Проверьте причины возвратов в кабинете WB",
            "Сверьте фото и описание с фактическим товаром",
            "Проверьте размерную сетку и комплектацию",
        ],
        "price": [
            "Проверьте активные скидки и акции",
            "Сверьте цену после СПП",
            "Сравните цену с конкурентами в нише",
        ],
        "volume": [
            "Проверьте остатки на складе WB",
            "Проверьте рекламную активность товара",
            "Сверьте цену относительно конкурентов",
        ],
    }
    return mapping.get(driver_type, ["Сверьте KPI по SKU в отчётах за период."])


def playbook_action(driver_type: str, sku: str, *, confidence: str) -> str:
    if confidence == "check_only":
        checks = playbook_checks(driver_type)
        return checks[0] if checks else f"Проверьте SKU {sku} в кабинете WB."
    actions = {
        "commission": f"Пересчитайте цену SKU {sku} после СПП под целевую маржу.",
        "logistics": f"Проверьте и при необходимости исправьте габариты упаковки SKU {sku} в карточке WB.",
        "returns": f"Обновите карточку SKU {sku}: фото, размеры и описание комплектации.",
        "price": f"Повысьте цену SKU {sku} или ограничьте участие в акциях с низкой маржой.",
        "volume": f"Проверьте остатки и рекламу SKU {sku}; при отсутствии на складе — пополните поставку.",
    }
    return actions.get(driver_type, f"Сверьте SKU {sku} и выберите корректирующее действие.")


def format_effect_label(low: int, high: int) -> str:
    if low <= 0 and high <= 0:
        return ""
    if low == high:
        return f"потенциально до {high:,} ₽".replace(",", " ")
    return f"потенциально {low:,}–{high:,} ₽".replace(",", " ")


def is_pricing_action(driver_type: str) -> bool:
    return driver_type in ("commission", "price")
