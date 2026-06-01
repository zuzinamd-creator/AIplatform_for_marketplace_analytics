"""AI cost governance API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AICostsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    period_start: date | None = None
    period_end: date | None = None
    runs_total: int
    estimated_cost_usd: float
    daily_cap_usd: float
    daily_spend_usd: float
    daily_cap_remaining_usd: float
    per_run_cap_usd: float
    by_workflow: list[dict] = Field(default_factory=list)
    by_prompt: list[dict] = Field(default_factory=list)
    by_provider: list[dict] = Field(default_factory=list)
    expensive_runs: list[dict] = Field(default_factory=list)
    repeated_prompts: list[dict] = Field(default_factory=list)
    generated_at: datetime


class AIProviderStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    primary_provider: str
    failover_provider: str | None
    circuit_breaker_open: bool
    streaming_enabled: bool
    cost_tracking_enabled: bool
    prompt_runtime_version: str
    providers: list[dict] = Field(default_factory=list)
    estimated_monthly_cost_usd: float | None = None
