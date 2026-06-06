import asyncio
import contextlib
import os
import signal
import sys
from pathlib import Path
from collections.abc import AsyncIterator
from uuid import UUID

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.observability import bind_job_context, clear_context, configure_logging, get_logger
from app.core.observability.context import set_correlation_id, track_duration
from app.core.queue import ClaimedJobRecord, get_queue_backend
from app.core.security_context import TenantSession
from app.core.startup_validation import validate_environment
from app.etl.pipeline import ETLPipeline
from app.etl.report_materialize import materialize_report_file
from app.etl.storage import read_report_file
from app.core.queue.etl_retry_policy import (
    EtlRetryableError,
    classify_retry_reason,
    compute_etl_retry_eligible_at,
    retry_audit_extra,
)
from app.etl.worker_shutdown import LegacyReportTooLargeError, WorkerShutdownRequested
from app.etl.wb.stream_pipeline import process_wb_streamed, wb_streaming_supported
from app.models.reliability import ProcessKind
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from app.runtime.containment.tenant_guard import TenantContainmentGuard
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches
from app.runtime.resilience.supervisor import ProcessSupervisor
from app.services.report_service import ReportService

logger = get_logger("worker")
_shutdown = asyncio.Event()
_current_job: ClaimedJobRecord | None = None
_process_supervisor: ProcessSupervisor | None = None


def _handle_shutdown(*_args) -> None:
    logger.info("worker_shutdown_signal_received")
    _shutdown.set()


def is_shutdown_requested() -> bool:
    return _shutdown.is_set()


async def _send_job_heartbeat(job_id: str, user_id: UUID) -> None:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            await get_queue_backend(db).heartbeat(job_id)
    logger.info("job_heartbeat", extra={"job_id": job_id})


async def _heartbeat_loop(job_id: str, user_id: UUID, interval: float | None = None) -> None:
    interval = interval or float(settings.worker_heartbeat_interval_seconds)
    while not _shutdown.is_set():
        if _current_job is None or str(_current_job.job_id) != job_id:
            return
        try:
            await _send_job_heartbeat(job_id, user_id)
        except Exception as exc:
            logger.warning("job_heartbeat_failed", extra={"error": str(exc)})
        await asyncio.sleep(interval)


@contextlib.asynccontextmanager
async def _job_heartbeat_scope(job_id: str, user_id: UUID) -> AsyncIterator[None]:
    """Keep queue heartbeat alive for the full job lifecycle (parse + persist + ack/fail)."""
    try:
        await _send_job_heartbeat(job_id, user_id)
    except Exception as exc:
        logger.warning("job_heartbeat_initial_failed", extra={"error": str(exc)})
    heartbeat_task = asyncio.create_task(_heartbeat_loop(job_id, user_id))
    try:
        yield
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task


async def process_next_job() -> bool:
    global _current_job
    set_correlation_id()
    switch = RuntimeKillSwitches.check(KillSwitchDomain.WORKER)
    if not switch.allowed:
        logger.info("worker_claim_blocked", extra={"reason": switch.reason})
        return False

    async with SessionLocal() as db:
        queue = get_queue_backend(db)
        recovered = await queue.recover_stale()
        if recovered:
            logger.info("queue_stale_jobs_recovered", extra={"queue_recovered": len(recovered)})
        job = await queue.claim()
        if not job:
            return False
        guard = await TenantContainmentGuard(db).check(job.user_id)
        if not guard.allowed:
            logger.warning(
                "worker_tenant_contained",
                extra={"user_id": str(job.user_id), "reason": guard.reason},
            )
            async with TenantSession.transaction(db, job.user_id):
                result = await db.execute(select(User).where(User.id == job.user_id))
                user = result.scalar_one_or_none()
                if user:
                    await ReportService(db, user).fail_job(
                        job.job_id,
                        error_message=f"tenant contained: {guard.reason}",
                        attempt_count=job.attempt_count,
                        max_attempts=job.max_attempts,
                        in_transaction=True,
                    )
            return True

    _current_job = job
    bind_job_context(job_id=str(job.job_id), report_id=str(job.report_id))
    logger.info(
        "job_claimed",
        extra={"attempt_count": job.attempt_count, "max_attempts": job.max_attempts},
    )
    logger.info("job_processing_started", extra={"job_id": str(job.job_id)})

    try:
        async with _job_heartbeat_scope(str(job.job_id), job.user_id):
            try:
                with track_duration(logger, "etl_process_content", job_id=str(job.job_id)):
                    marketplace = Marketplace(job.marketplace)
                    if (
                        marketplace == Marketplace.WILDBERRIES
                        and wb_streaming_supported(job.original_filename)
                    ):
                        suffix = Path(job.original_filename).suffix.lower() or ".xlsx"
                        async with SessionLocal() as parse_db:
                            report_row = await parse_db.execute(
                                select(Report).where(Report.id == job.report_id)
                            )
                            report_for_parse = report_row.scalar_one_or_none()
                            if not report_for_parse:
                                raise ValueError("Report not found for streaming parse")
                            with materialize_report_file(
                                job.file_path,
                                suffix=suffix,
                                expected_checksum=report_for_parse.file_checksum,
                            ) as path:
                                etl_result = await process_wb_streamed(
                                    db=parse_db,
                                    user_id=job.user_id,
                                    report=report_for_parse,
                                    path=path,
                                    filename=job.original_filename,
                                    job_id=job.job_id,
                                    shutdown_check=is_shutdown_requested,
                                )
                    else:
                        content = read_report_file(
                            job.file_path,
                            filename=job.original_filename,
                        )
                        etl_result = ETLPipeline.process_content(
                            report_id=job.report_id,
                            report_created_at=job.report_created_at,
                            filename=job.original_filename,
                            content=content,
                            marketplace=marketplace,
                            report_type=ReportType(job.report_type),
                        )
            except EtlRetryableError as exc:
                await _mark_job_failed_or_retry(job, str(exc), exc=exc)
                return True
            except WorkerShutdownRequested as exc:
                logger.warning(
                    "job_graceful_shutdown",
                    extra={
                        "job_id": str(job.job_id),
                        "phase": exc.phase,
                        "chunks_completed": exc.chunks_completed,
                    },
                )
                await _mark_job_failed_or_retry(
                    job,
                    "Worker shutdown: текущий чанк сохранён, задача будет повторена",
                    exc=exc,
                )
                return True
            except LegacyReportTooLargeError as exc:
                await _mark_job_failed_or_retry(job, str(exc), exc=exc)
                return True
            except Exception as exc:
                logger.exception("job_processing_failed", extra={"error": str(exc)})
                await _mark_job_failed_or_retry(job, str(exc), exc=exc)
                return True

            if _shutdown.is_set():
                logger.warning("job_interrupted_by_shutdown", extra={"job_id": str(job.job_id)})
                await _mark_job_failed_or_retry(
                    job,
                    "Worker shutdown during processing (post-parse)",
                )
                return True

            try:
                async with SessionLocal() as db:
                    report_row = await db.execute(
                        select(Report).where(Report.id == job.report_id)
                    )
                    report = report_row.scalar_one_or_none()
                    user_row = await db.execute(select(User).where(User.id == job.user_id))
                    user = user_row.scalar_one_or_none()

                    if not report or not user:
                        logger.error("worker_persist_target_missing")
                        async with TenantSession.transaction(db, job.user_id):
                            if user:
                                await ReportService(db, user).fail_job(
                                    job.job_id,
                                    error_message="Persist target missing",
                                    attempt_count=job.attempt_count,
                                    max_attempts=job.max_attempts,
                                    in_transaction=True,
                                )
                        return True

                    await db.commit()

                    report_service = ReportService(db, user)
                    pipeline = ETLPipeline(db, job.user_id)
                    with track_duration(logger, "etl_persist_result", job_id=str(job.job_id)):
                        await pipeline.persist_result(
                            report,
                            etl_result,
                            report_service,
                            job_id=job.job_id,
                            in_transaction=False,
                        )
                    async with TenantSession.transaction(db, job.user_id):
                        await report_service.ack_job(
                            job.job_id,
                            report_id=job.report_id,
                            in_transaction=True,
                        )
            except EtlRetryableError as exc:
                await _mark_job_failed_or_retry(job, str(exc), exc=exc)
                return True
            except WorkerShutdownRequested as exc:
                logger.warning(
                    "job_graceful_shutdown_during_persist",
                    extra={"job_id": str(job.job_id), "phase": exc.phase},
                )
                await _mark_job_failed_or_retry(
                    job,
                    "Worker shutdown: текущий этап persist завершён, задача будет повторена",
                    exc=exc,
                )
                return True
            except Exception as exc:
                logger.exception("job_persist_failed", extra={"error": str(exc)})
                await _mark_job_failed_or_retry(job, str(exc), exc=exc)
                return True

        logger.info("job_completed")
        return True
    finally:
        _current_job = None
        clear_context()


async def _mark_job_failed_or_retry(
    job: ClaimedJobRecord,
    error_message: str,
    *,
    exc: BaseException | None = None,
) -> None:
    poison = job.attempt_count >= job.max_attempts
    retry_reason = classify_retry_reason(error_message, exc)
    log_event = "job_dead_lettered" if poison else "job_failed_will_retry"
    retry_eligible_at = (
        None if poison else compute_etl_retry_eligible_at(job.attempt_count)
    )
    logger.error(
        log_event,
        extra=retry_audit_extra(
            job_id=str(job.job_id),
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            retry_reason=retry_reason,
            retry_eligible_at=retry_eligible_at,
            error_message=error_message,
        ),
    )

    async with SessionLocal() as db:
        async with TenantSession.transaction(db, job.user_id):
            result = await db.execute(select(User).where(User.id == job.user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            await ReportService(db, user).fail_job(
                job.job_id,
                error_message=error_message,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                in_transaction=True,
                retry_reason=retry_reason.value,
            )


async def run_worker() -> None:
    global _process_supervisor
    configure_logging(settings.log_level)
    env_report = validate_environment()
    if not env_report.ok:
        logger.error("worker_startup_validation_failed", extra={"errors": env_report.errors})
        return
    switch = RuntimeKillSwitches.check(KillSwitchDomain.WORKER)
    if not switch.allowed:
        logger.warning("worker_disabled", extra={"reason": switch.reason})
        return

    _process_supervisor = ProcessSupervisor(process_kind=ProcessKind.ETL_WORKER, shutdown=_shutdown)
    _process_supervisor.start()
    logger.info("worker_started")
    poll_interval = 2.0

    try:
        while not _shutdown.is_set():
            try:
                processed = await process_next_job()
                if not processed:
                    try:
                        await asyncio.wait_for(_shutdown.wait(), timeout=poll_interval)
                    except TimeoutError:
                        pass
            except Exception as exc:
                logger.exception("worker_loop_error", extra={"error": str(exc)})
                try:
                    await asyncio.wait_for(_shutdown.wait(), timeout=5.0)
                except TimeoutError:
                    pass
    finally:
        if _process_supervisor is not None:
            await _process_supervisor.stop()
        await engine.dispose()
        clear_context()
        logger.info("worker_stopped")


def main() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
