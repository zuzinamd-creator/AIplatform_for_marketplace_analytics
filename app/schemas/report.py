from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import Marketplace, ReportStatus, ReportType


class ReportResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    user_id: UUID
    marketplace: Marketplace
    report_type: ReportType
    original_filename: str = Field(min_length=1, max_length=512)
    file_path: str | None = Field(default=None, min_length=1, max_length=1024)
    status: ReportStatus
    row_count: int | None = Field(default=None, ge=0)
    error_message: str | None = Field(default=None, min_length=1, max_length=4096)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)
    claimed_at: datetime | None = None
    processed_at: datetime | None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime
    updated_at: datetime


class ReportUploadResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    report: ReportResponse
    message: str = Field(
        default="Report uploaded and queued for processing",
        min_length=1,
        max_length=255,
    )
