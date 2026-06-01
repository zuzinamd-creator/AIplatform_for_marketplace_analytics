import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.observability.context import logging_context
from app.core.observability.etl_metrics import metrics_context


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(logging_context())
        payload.update(metrics_context())

        for key in (
            "duration_ms",
            "status",
            "error",
            "queue_recovered",
            "jobs_processed",
            "attempt_count",
            "max_attempts",
            "status_code",
            "method",
            "path",
            "user_id",
            "report_id",
            "correlation_id",
            "operation_stage",
            "semantics_version",
            "rebuild_window",
            "rows_processed",
            "rows_rejected",
            "rebuild_duration_ms",
            "rebuild_rows_streamed",
            "snapshot_rows_written",
            "advisory_lock_contention",
            "rebuild_full_vs_incremental",
            "checksum_mismatch_count",
            "ai_generation_duration",
            "ai_prompt_tokens",
            "ai_completion_tokens",
            "bulk_upsert_batch_size",
            "stream_chunk_size",
            "anomaly_count",
        ):
            if hasattr(record, key):
                value = getattr(record, key)
                if value is not None:
                    payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
