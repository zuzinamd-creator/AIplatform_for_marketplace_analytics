from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CostImportIssue(BaseModel):
    model_config = ConfigDict(strict=True)

    severity: str = Field(description="warning|error")
    code: str
    message: str
    row_index: int | None = None


class CostImportPreviewRow(BaseModel):
    model_config = ConfigDict(strict=True)

    row_index: int
    internal_sku: str | None = None
    effective_from: date | None = None
    product_cost: Decimal | None = None
    packaging_cost: Decimal | None = None
    inbound_logistics_cost: Decimal | None = None
    additional_cost: Decimal | None = None
    currency: str | None = None
    comment: str | None = None
    total_cost: Decimal | None = None


class CostImportPreviewResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    detected_columns: dict[str, str | None]
    total_rows: int
    preview_rows: list[CostImportPreviewRow]
    issues: list[CostImportIssue]


class CostImportResultResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    detected_columns: dict[str, str | None]
    total_rows: int
    imported_rows: int
    skipped_rows: int
    imported_distinct_skus: int
    invalid_sku_count: int
    issues: list[CostImportIssue]
