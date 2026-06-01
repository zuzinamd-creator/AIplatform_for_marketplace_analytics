"""Best-effort batched persistence for ETL anomalies."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.domain.etl.anomaly_draft import EtlAnomalyDraft
from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches
from app.models.etl.anomaly import EtlAnomaly

logger = get_logger(__name__)


class EtlAnomalyPersistService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def persist_best_effort(self, anomalies: list[EtlAnomalyDraft]) -> int:
        """
        Bulk insert anomalies; never raises to caller.

        Returns count persisted, or 0 on failure (structured log emitted).
        """
        if not anomalies:
            return 0
        try:
            return await self._bulk_insert(anomalies)
        except Exception as exc:
            logger.exception(
                "etl_anomaly_persist_failed",
                extra={
                    "user_id": str(self.user_id),
                    "operation_stage": "anomaly_persist",
                    "anomaly_count": len(anomalies),
                    "error": str(exc),
                },
            )
            return 0

    async def _bulk_insert(self, anomalies: list[EtlAnomalyDraft]) -> int:
        values = [_to_row(self.user_id, draft) for draft in anomalies]
        stmt = insert(EtlAnomaly)
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(stmt, batch)
        return len(values)


def _to_row(user_id: UUID, draft: EtlAnomalyDraft) -> dict:
    return {
        "id": uuid4(),
        "user_id": user_id,
        "report_id": draft.report_id,
        "source_file_name": draft.source_file_name,
        "row_number": draft.row_number,
        "severity": draft.severity,
        "anomaly_type": draft.anomaly_type,
        "parser_stage": draft.parser_stage,
        "raw_payload": draft.raw_payload,
        "normalized_payload": draft.normalized_payload,
        "error_message": draft.error_message,
        "semantics_version": draft.semantics_version,
    }
