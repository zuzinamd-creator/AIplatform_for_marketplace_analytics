from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot


def cost_on_date(history: list[SkuCostSnapshot], on_date: date) -> Decimal | None:
    """Nearest valid cost snapshot: latest effective_from on or before operation_date."""
    applicable = [item for item in history if item.effective_from <= on_date]
    if not applicable:
        return None
    latest = max(applicable, key=lambda item: item.effective_from)
    return latest.total_unit_cost
