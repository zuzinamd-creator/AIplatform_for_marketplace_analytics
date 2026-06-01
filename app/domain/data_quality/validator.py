"""Data quality rules — emit anomaly drafts, never silent correction."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.domain.etl.anomaly_draft import EtlAnomalyDraft
from app.domain.inventory.types import InventoryMovementDraft
from app.parsers.wb.semantics import SEMANTICS_VERSION
from app.parsers.wb.semantics_registry import SEMANTICS_REGISTRY


class DataQualityValidator:
    @staticmethod
    def validate_wb_process(
        *,
        report_id: UUID,
        source_file_name: str,
        inventory_movements: list[InventoryMovementDraft],
        today: date | None = None,
    ) -> list[EtlAnomalyDraft]:
        ref = today or date.today()
        anomalies: list[EtlAnomalyDraft] = []
        seen_keys: dict[tuple[str, str, str, str], int] = defaultdict(int)

        if SEMANTICS_VERSION not in SEMANTICS_REGISTRY:
            anomalies.append(
                _draft(
                    report_id=report_id,
                    source_file_name=source_file_name,
                    row_number=None,
                    severity="error",
                    anomaly_type="unsupported_semantics",
                    parser_stage="inventory",
                    raw_payload={"semantics_version": SEMANTICS_VERSION},
                    error_message=f"Unsupported default semantics version: {SEMANTICS_VERSION}",
                    semantics_version=SEMANTICS_VERSION,
                )
            )

        for movement in inventory_movements:
            raw = dict(movement.raw_payload or {})
            row_number = _row_index(raw)
            key = (
                movement.sku or "",
                movement.warehouse_name or "",
                movement.source_row_id,
                movement.operation_type.value,
            )
            seen_keys[key] += 1
            if seen_keys[key] > 1:
                anomalies.append(
                    _draft(
                        report_id=report_id,
                        source_file_name=source_file_name,
                        row_number=row_number,
                        severity="warning",
                        anomaly_type="duplicate_replay",
                        parser_stage="inventory",
                        raw_payload=raw,
                        normalized_payload=movement.canonical_payload,
                        error_message="Duplicate source_row_id and operation_type in batch",
                        semantics_version=movement.semantics_version,
                    )
                )

            if movement.operation_date > ref:
                anomalies.append(
                    _draft(
                        report_id=report_id,
                        source_file_name=source_file_name,
                        row_number=row_number,
                        severity="warning",
                        anomaly_type="future_dated_operation",
                        parser_stage="inventory",
                        raw_payload=raw,
                        normalized_payload=movement.canonical_payload,
                        error_message=f"Operation date {movement.operation_date} is after {ref}",
                        semantics_version=movement.semantics_version,
                    )
                )

            if movement.quantity_delta < 0 and movement.operation_type.value in {
                "inbound",
                "return",
                "compensation",
            }:
                anomalies.append(
                    _draft(
                        report_id=report_id,
                        source_file_name=source_file_name,
                        row_number=row_number,
                        severity="warning",
                        anomaly_type="impossible_warehouse_transition",
                        parser_stage="inventory",
                        raw_payload=raw,
                        normalized_payload=movement.canonical_payload,
                        error_message="Negative quantity on inbound-class operation",
                        semantics_version=movement.semantics_version,
                    )
                )

            for field_name in ("cost_per_unit", "sale_price_per_unit"):
                if field_name in raw and not _decimal_ok(raw.get(field_name)):
                    anomalies.append(
                        _draft(
                            report_id=report_id,
                            source_file_name=source_file_name,
                            row_number=row_number,
                            severity="error",
                            anomaly_type="invalid_decimal_coercion",
                            parser_stage="normalize",
                            raw_payload=raw,
                            normalized_payload=movement.canonical_payload,
                            error_message=f"Invalid decimal in field {field_name}",
                            semantics_version=movement.semantics_version,
                        )
                    )

        return anomalies


def _draft(**kwargs: Any) -> EtlAnomalyDraft:
    return EtlAnomalyDraft(**kwargs)


def _row_index(raw: dict[str, Any]) -> int | None:
    idx = raw.get("parser_row_index") or raw.get("row_index")
    if idx is None:
        return None
    try:
        return int(idx)
    except (TypeError, ValueError):
        return None


def _decimal_ok(value: object) -> bool:
    if value is None:
        return True
    try:
        Decimal(str(value))
        return True
    except (InvalidOperation, ValueError):
        return False
