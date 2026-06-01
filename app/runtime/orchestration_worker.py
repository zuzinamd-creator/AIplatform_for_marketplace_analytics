"""
Orchestration worker — runtime control plane loop (separate from ETL report worker).

Run: python -m app.runtime.orchestration_worker
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from uuid import UUID

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.observability import configure_logging, get_logger
from app.core.observability.context import set_correlation_id
from app.core.startup_validation import validate_environment
from app.models.reliability import ProcessKind
from app.runtime.control_plane.coordinator import RuntimeControlPlane
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches
from app.runtime.resilience.lease import OrchestratorLeaseService
from app.runtime.resilience.supervisor import ProcessSupervisor
from app.runtime.runtime_guards import RuntimeGuardState

logger = get_logger("orchestration_worker")
_shutdown = asyncio.Event()
_guard_state = RuntimeGuardState()
_process_supervisor: ProcessSupervisor | None = None
_lease_holder_id: UUID | None = None


def _handle_shutdown(*_args) -> None:
    logger.info("orchestration_worker_shutdown_signal_received")
    _shutdown.set()


async def run_cycle() -> bool:
    global _lease_holder_id
    set_correlation_id()
    if _lease_holder_id is not None:
        async with SessionLocal() as db:
            lease = await OrchestratorLeaseService(db, holder_id=_lease_holder_id).try_acquire()
            if not lease.acquired:
                logger.info("orchestrator_lease_not_held", extra={"reason": lease.reason})
                return False
    async with SessionLocal() as db:
        result = await RuntimeControlPlane(db, guard_state=_guard_state).run_cycle()
        logger.info(
            "control_plane_cycle",
            extra={
                "dispatched": result.dispatched_rebuild,
                "health_score": result.health.overall_score,
                "severity": result.health.overall_severity.value,
                "schedules": list(result.schedules_run),
            },
        )
        return result.dispatched_rebuild


async def run_orchestrator() -> None:
    global _process_supervisor, _lease_holder_id
    configure_logging(settings.log_level)
    env_report = validate_environment()
    if not env_report.ok:
        logger.error("orchestrator_startup_validation_failed", extra={"errors": env_report.errors})
        return
    switch = RuntimeKillSwitches.check(KillSwitchDomain.ORCHESTRATOR)
    if not switch.allowed:
        logger.warning("orchestrator_disabled", extra={"reason": switch.reason})
        return

    async with SessionLocal() as db:
        lease_svc = OrchestratorLeaseService(db)
        lease = await lease_svc.try_acquire()
        if not lease.acquired:
            logger.error("orchestrator_lease_denied", extra={"reason": lease.reason})
            return
        _lease_holder_id = lease_svc.holder_id

    _process_supervisor = ProcessSupervisor(
        process_kind=ProcessKind.ORCHESTRATOR,
        shutdown=_shutdown,
    )
    _process_supervisor.start()

    logger.info(
        "orchestration_worker_started",
        extra={
            "poll_interval_seconds": settings.orchestrator_poll_interval_seconds,
            "autonomy_enabled": settings.runtime_autonomy_enabled,
            "lease_holder": str(_lease_holder_id),
        },
    )

    cycles_run = 0
    try:
        while not _shutdown.is_set():
            if (
                settings.orchestrator_max_cycles_per_run > 0
                and cycles_run >= settings.orchestrator_max_cycles_per_run
            ):
                break
            try:
                await run_cycle()
                cycles_run += 1
            except Exception as exc:
                logger.exception("orchestration_cycle_error", extra={"error": str(exc)})

            if _shutdown.is_set():
                break
            try:
                await asyncio.wait_for(
                    _shutdown.wait(),
                    timeout=settings.orchestrator_poll_interval_seconds,
                )
            except TimeoutError:
                pass
    finally:
        if _process_supervisor is not None:
            await _process_supervisor.stop()
        if _lease_holder_id is not None:
            async with SessionLocal() as db:
                await OrchestratorLeaseService(db, holder_id=_lease_holder_id).release()
        await engine.dispose()
        logger.info("orchestration_worker_stopped", extra={"cycles_run": cycles_run})


def main() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    asyncio.run(run_orchestrator())


if __name__ == "__main__":
    main()
