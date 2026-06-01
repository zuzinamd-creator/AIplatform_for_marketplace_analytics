from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from app.etl.wb.types import WbFinancialProcessResult


class RawDataSnapshot(TypedDict):
    row_count: int
    columns: list[str]
    records: list[dict[str, str | int | float | None]]


class AnalyticsPayload(TypedDict, total=False):
    report_id: str
    report_date: str
    marketplace_type: str
    sku_count: int
    total_revenue: str | None
    total_profit: str | None
    margin: str | None
    top_skus_summary: list[dict[str, object]]
    anomalies: list[dict[str, object]]
    inventory_losses_units: int
    inventory_losses_cost: str
    inventory_losses_sale_value: str
    warehouse_discrepancies: list[dict[str, object]]
    top_loss_skus: list[dict[str, object]]


@dataclass(frozen=True)
class ETLResult:
    raw_data: RawDataSnapshot
    row_count: int
    analytics_payload: AnalyticsPayload
    wb_financial: "WbFinancialProcessResult | None" = None
