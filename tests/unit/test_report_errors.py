"""User-facing failed-report error hints."""

from app.models.job import EtlJob, JobStatus
from app.schemas.report_errors import is_report_retryable, user_facing_error_hint


def test_retryable_for_dead_letter() -> None:
    job = EtlJob(
        user_id=None,  # type: ignore[arg-type]
        report_id=None,  # type: ignore[arg-type]
        status=JobStatus.DEAD_LETTER,
        attempt_count=3,
        max_attempts=3,
    )
    assert is_report_retryable(job) is True


def test_closed_transaction_hint() -> None:
    msg = "Can't operate on closed transaction inside context manager."
    hint = user_facing_error_hint(last_error=msg, job=None)
    assert hint is not None
    assert "Повторить обработку" in hint
