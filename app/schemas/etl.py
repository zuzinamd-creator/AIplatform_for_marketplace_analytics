from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FinancialValue(BaseModel):
    model_config = ConfigDict(strict=True)

    value: Decimal = Field(gt=0)


class QuantityValue(BaseModel):
    model_config = ConfigDict(strict=True)

    value: int = Field(ge=0)
