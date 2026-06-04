from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    internal_sku: str = Field(min_length=1, max_length=128)
    effective_from: date
    product_cost: Decimal = Field(gt=0)
    packaging_cost: Decimal = Field(default=Decimal("0"), ge=0)
    inbound_logistics_cost: Decimal = Field(default=Decimal("0"), ge=0)
    additional_cost: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    comment: str | None = Field(default=None, max_length=1024)


class CostUpdateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    product_cost: Decimal | None = Field(default=None, gt=0)
    packaging_cost: Decimal | None = Field(default=None, ge=0)
    inbound_logistics_cost: Decimal | None = Field(default=None, ge=0)
    additional_cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    comment: str | None = Field(default=None, max_length=1024)


class CostResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    internal_sku: str
    product_cost: Decimal
    packaging_cost: Decimal
    inbound_logistics_cost: Decimal
    additional_cost: Decimal
    cost: Decimal
    currency: str
    effective_from: date
    comment: str | None
