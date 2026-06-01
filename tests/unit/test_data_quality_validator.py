from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.data_quality.validator import DataQualityValidator
from app.domain.inventory.types import InventoryMovementDraft
from app.models.inventory.enums import InventoryOperationType


def _movement(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    source_row_id: str = "row-1",
    raw: dict | None = None,
) -> InventoryMovementDraft:
    payload = raw or {"parser_row_index": 2}
    return InventoryMovementDraft(
        operation_date=operation_date,
        sku="SKU-1",
        nm_id=None,
        warehouse_name="WH-1",
        operation_type=operation_type,
        quantity_delta=quantity_delta,
        cost_per_unit=None,
        sale_price_per_unit=None,
        total_cost_delta=Decimal("0"),
        total_sale_delta=Decimal("0"),
        source_row_id=source_row_id,
        semantics_version="1.0",
        raw_payload={str(k): str(v) for k, v in payload.items()},
        canonical_payload={"sku": "SKU-1"},
    )


def test_future_dated_operation_detected() -> None:
    report_id = uuid4()
    anomalies = DataQualityValidator.validate_wb_process(
        report_id=report_id,
        source_file_name="report.xlsx",
        inventory_movements=[
            _movement(
                operation_date=date(2099, 1, 1),
                operation_type=InventoryOperationType.INBOUND,
                quantity_delta=1,
            )
        ],
        today=date(2026, 1, 1),
    )
    assert any(a.anomaly_type == "future_dated_operation" for a in anomalies)


def test_duplicate_replay_detected() -> None:
    report_id = uuid4()
    shared = dict(
        operation_date=date(2026, 1, 5),
        operation_type=InventoryOperationType.SALE,
        quantity_delta=-1,
    )
    anomalies = DataQualityValidator.validate_wb_process(
        report_id=report_id,
        source_file_name="report.xlsx",
        inventory_movements=[
            _movement(**shared, source_row_id="dup"),  # type: ignore[arg-type]
            _movement(**shared, source_row_id="dup"),  # type: ignore[arg-type]
        ],
        today=date(2026, 1, 10),
    )
    assert any(a.anomaly_type == "duplicate_replay" for a in anomalies)


def test_invalid_decimal_coercion_detected() -> None:
    report_id = uuid4()
    anomalies = DataQualityValidator.validate_wb_process(
        report_id=report_id,
        source_file_name="report.xlsx",
        inventory_movements=[
            _movement(
                operation_date=date(2026, 1, 5),
                operation_type=InventoryOperationType.INBOUND,
                quantity_delta=1,
                raw={"parser_row_index": "1", "cost_per_unit": "not-a-decimal"},
            )
        ],
        today=date(2026, 1, 10),
    )
    assert any(a.anomaly_type == "invalid_decimal_coercion" for a in anomalies)
