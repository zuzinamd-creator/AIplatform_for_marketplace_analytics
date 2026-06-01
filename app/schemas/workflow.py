from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowEventCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    recommendation_id: UUID | None = None
    event_type: str = Field(min_length=1, max_length=48)
    note: str | None = Field(default=None, max_length=4000)
    reminder_at: datetime | None = None
    metadata_json: dict | None = None


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: UUID
    recommendation_id: UUID | None = None
    event_type: str
    note: str | None = None
    reminder_at: datetime | None = None
    metadata_json: dict | None = None
    created_at: datetime


class WorkflowHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    recommendation_id: UUID | None = None
    items: list[WorkflowEventResponse]

