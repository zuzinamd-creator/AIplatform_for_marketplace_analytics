from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class EtlAnomalyDraft:
    report_id: UUID | None
    source_file_name: str
    row_number: int | None
    severity: str
    anomaly_type: str
    parser_stage: str
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any] | None
    error_message: str
    semantics_version: str | None = None
