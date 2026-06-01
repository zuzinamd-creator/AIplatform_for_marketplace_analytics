from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.metrics import MetricPeriod
from app.models.report import Marketplace


class ProductResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    user_id: UUID
    marketplace: Marketplace
    external_sku: str = Field(min_length=1, max_length=128)
    internal_sku: str | None = Field(default=None, min_length=1, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=512)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    created_at: datetime
    updated_at: datetime


class SKUMappingResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    user_id: UUID
    internal_sku: str = Field(min_length=1, max_length=128)
    marketplace: Marketplace
    marketplace_sku: str = Field(min_length=1, max_length=128)
    created_at: datetime
    updated_at: datetime


class CostHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    user_id: UUID
    internal_sku: str = Field(min_length=1, max_length=128)
    cost: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    effective_from: date
    effective_to: date | None = None
    source_report_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MetricResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    user_id: UUID
    internal_sku: str = Field(min_length=1, max_length=128)
    marketplace: Marketplace
    period: MetricPeriod
    period_start: date
    period_end: date
    revenue: Decimal | None = Field(default=None, gt=0)
    profit: Decimal | None = Field(default=None, gt=0)
    orders_count: int | None = Field(default=None, ge=0)
    units_sold: int | None = Field(default=None, ge=0)
    margin: Decimal | None = Field(default=None, gt=0)
    created_at: datetime
    updated_at: datetime
