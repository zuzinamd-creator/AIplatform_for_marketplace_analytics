from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.analytics.aggregation import DailyAggregateDraft, SkuDailyMetricDraft
from app.domain.etl.anomaly_draft import EtlAnomalyDraft
from app.domain.finance.types import LedgerEntryDraft
from app.domain.inventory.types import InventoryMovementDraft
from app.domain.reconciliation.calculator import ReconciliationResult
from app.etl.types import AnalyticsPayload, RawDataSnapshot
from app.parsers.wb.base import NormalizedWbRow


@dataclass(frozen=True)
class WbFinancialProcessResult:
    report_id: UUID
    parser_name: str
    parser_version: str
    raw_snapshot: RawDataSnapshot
    normalized_rows: list[NormalizedWbRow]
    ledger_entries: list[LedgerEntryDraft]
    inventory_movements: list[InventoryMovementDraft]
    reconciliation: ReconciliationResult
    daily_aggregates: list[DailyAggregateDraft]
    sku_daily_metrics: list[SkuDailyMetricDraft]
    analytics_payload: AnalyticsPayload
    default_date: date
    row_count: int
    etl_anomalies: tuple[EtlAnomalyDraft, ...] = ()
