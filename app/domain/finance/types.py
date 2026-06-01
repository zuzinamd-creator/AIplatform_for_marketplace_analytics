from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.finance.enums import LedgerOperationType


@dataclass(frozen=True)
class LedgerEntryDraft:
    operation_date: date
    sku: str | None
    nm_id: str | None
    operation_type: LedgerOperationType
    amount: Decimal
    currency: str
    source_row_id: str
    entry_metadata: dict[str, str] | None = None


@dataclass(frozen=True)
class SkuCostSnapshot:
    sku: str
    effective_from: date
    product_cost: Decimal
    packaging_cost: Decimal
    inbound_logistics_cost: Decimal
    additional_cost: Decimal
    currency: str

    @property
    def total_unit_cost(self) -> Decimal:
        return self.product_cost + self.packaging_cost + self.inbound_logistics_cost + self.additional_cost
