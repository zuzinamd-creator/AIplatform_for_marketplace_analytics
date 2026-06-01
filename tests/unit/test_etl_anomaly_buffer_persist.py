from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.domain.etl.anomaly_draft import EtlAnomalyDraft
from app.etl.anomaly_buffer import EtlAnomalyBuffer
from app.etl.anomaly_persist import EtlAnomalyPersistService
from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches


def test_buffer_collects_without_db() -> None:
    buf = EtlAnomalyBuffer()
    draft = EtlAnomalyDraft(
        report_id=uuid4(),
        source_file_name="f.xlsx",
        row_number=1,
        severity="warning",
        anomaly_type="validation_warning",
        parser_stage="inventory",
        raw_payload={"k": "v"},
        normalized_payload=None,
        error_message="test",
        semantics_version="1.0",
    )
    buf.add(draft)
    assert len(buf) == 1
    assert buf.peek()[0].anomaly_type == "validation_warning"
    drained = buf.drain()
    assert len(drained) == 1
    assert len(buf) == 0


def test_iter_batches_chunks_large_inserts() -> None:
    values = list(range(INSERT_BATCH_SIZE * 2 + 3))
    batches = list(iter_batches(values, batch_size=INSERT_BATCH_SIZE))
    assert len(batches) == 3
    assert sum(len(b) for b in batches) == len(values)


@pytest.mark.asyncio
async def test_persist_best_effort_never_raises_on_db_error() -> None:
    db = MagicMock()
    db.execute = AsyncMock(side_effect=RuntimeError("db down"))
    user_id = uuid4()
    drafts = [
        EtlAnomalyDraft(
            report_id=uuid4(),
            source_file_name="f.xlsx",
            row_number=None,
            severity="error",
            anomaly_type="parse_error",
            parser_stage="parse",
            raw_payload={},
            normalized_payload=None,
            error_message="boom",
            semantics_version="1.0",
        )
    ]
    count = await EtlAnomalyPersistService(db, user_id).persist_best_effort(drafts)
    assert count == 0
