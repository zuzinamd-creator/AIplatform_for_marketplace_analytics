"""AI usage + cost tracking schemas (tenant-scoped)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AIUsageQuery(BaseModel):
    model_config = ConfigDict(strict=True)

    start: date | None = None
    end: date | None = None


class AIUsageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    period_start: date | None = None
    period_end: date | None = None
    runs_total: int
    prompt_tokens: int
    completion_tokens: int
    tokens_total: int
    estimated_cost_usd: float | None = None
    by_provider: list[dict] = Field(default_factory=list)
    generated_at: datetime
