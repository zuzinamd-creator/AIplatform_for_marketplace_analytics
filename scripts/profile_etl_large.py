"""
Instrumented ETL profile for large_wb_test.xlsx.

Measures wall-clock per stage and SQL query counts/times per stage.
Run: python scripts/profile_etl_large.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.environment import detect_environment

from sqlalchemy import delete, event, text
from sqlalchemy.engine import Engine

from app.core.database import SessionLocal, engine
from app.core.security_context import TenantSession
from app.etl.loaders import load_file_to_dataframe
from app.etl.pipeline import ETLPipeline
from app.etl.storage import read_report_file
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist import WbFinancialPersistService, _earliest_movement_date
from app.etl.wb.processor import WbFinancialProcessor
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from app.parsers.wb import parse_wb_report
from app.services.report_service import ReportService

# --- SQL profiler ---
_current_stage: ContextVar[str] = ContextVar("profile_stage", default="unknown")


@dataclass
class StageSqlStats:
    count: int = 0
    total_ms: float = 0.0
    statements: list[str] = field(default_factory=list)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0


@dataclass
class SqlProfiler:
    stages: dict[str, StageSqlStats] = field(default_factory=lambda: defaultdict(StageSqlStats))
    _pending: dict[int, tuple[str, float]] = field(default_factory=dict)

    def install(self) -> None:
        sync_engine = engine.sync_engine

        @event.listens_for(sync_engine, "before_cursor_execute")
        def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            stage = _current_stage.get()
            self._pending[id(cursor)] = (stage, time.perf_counter())

        @event.listens_for(sync_engine, "after_cursor_execute")
        def _after(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            started = self._pending.pop(id(cursor), None)
            if started is None:
                return
            stage, t0 = started
            elapsed_ms = (time.perf_counter() - t0) * 1000
            stats = self.stages[stage]
            stats.count += 1
            stats.total_ms += elapsed_ms
            if len(stats.statements) < 5:
                stats.statements.append(_normalize_sql(statement))

    def remove(self) -> None:
        event.remove(Engine, "before_cursor_execute", _before)  # type: ignore[name-defined]
        event.remove(Engine, "after_cursor_execute", _after)  # type: ignore[name-defined]


def _normalize_sql(statement: str) -> str:
    s = " ".join(statement.split())
    if len(s) > 120:
        s = s[:117] + "..."
    return s


def _set_stage(name: str):
    return _current_stage.set(name)


def _reset_stage(token) -> None:
    _current_stage.reset(token)


STORAGE_PATH = (
    "reports/1267cd81-ca57-4773-8f5c-0febe84488f4/"
    "2e9490d8-d13f-4ec6-a8c5-7f9d01d2f649/2e9490d8-d13f-4ec6-a8c5-7f9d01d2f649.xlsx"
)


async def profile_persist_stages(
    db,
    user: User,
    report: Report,
    wb_result,
    profiler: SqlProfiler,
) -> dict[str, float]:
    """Run persist sub-stages individually with SQL stage tags."""
    timings: dict[str, float] = {}
    persist = WbFinancialPersistService(db, user.id)
    snapshot_service = InventorySnapshotRebuildService(db, user.id)

    token = _set_stage("opening_balance_validation")
    t0 = time.perf_counter()
    await snapshot_service.validate_opening_balances_for_movements(
        wb_result.inventory_movements,
        exclude_report_id=report.id,
    )
    timings["opening_balance_validation"] = time.perf_counter() - t0
    _reset_stage(token)

    token = _set_stage("persist_layers")
    t0 = time.perf_counter()
    await persist._persist_raw_report(
        report=report,
        file_checksum=report.file_checksum or "",
        storage_uri=report.file_path or "",
        result=wb_result,
    )
    await persist._persist_normalized_rows(report_id=report.id, result=wb_result)
    await persist._persist_ledger(report_id=report.id, result=wb_result)
    await persist._persist_inventory_ledger(report_id=report.id, result=wb_result)
    await persist._persist_reconciliation(report_id=report.id, result=wb_result)
    timings["persist_layers"] = time.perf_counter() - t0
    _reset_stage(token)

    token = _set_stage("inventory_rebuild")
    t0 = time.perf_counter()
    earliest = _earliest_movement_date(wb_result)
    await snapshot_service.rebuild(earliest_affected_date=earliest)
    timings["inventory_rebuild"] = time.perf_counter() - t0
    _reset_stage(token)

    token = _set_stage("rebuild_aggregates")
    t0 = time.perf_counter()
    await persist._rebuild_aggregates(result=wb_result, report_id=report.id)
    timings["rebuild_aggregates"] = time.perf_counter() - t0
    _reset_stage(token)

    return timings


async def main() -> None:
    env = detect_environment()
    if env.mode == "MAIN" and os.environ.get("PROFILE_ALLOW_MAIN") != "1":
        raise SystemExit(
            "Refusing to run ETL profile on MAIN database. "
            "Set PROFILE_ALLOW_MAIN=1 only on a disposable clone, never on production tenant data."
        )

    profiler = SqlProfiler()
    profiler.install()

    wall: dict[str, float] = {}
    total_t0 = time.perf_counter()

    # --- read_report_file ---
    t0 = time.perf_counter()
    local_xlsx = os.environ.get("PROFILE_LOCAL_XLSX")
    if local_xlsx:
        content = Path(local_xlsx).read_bytes()
    else:
        content = read_report_file(STORAGE_PATH)
    wall["read_report_file"] = time.perf_counter() - t0
    file_mb = len(content) / (1024 * 1024)

    report_id = uuid4()
    user_id = uuid4()
    file_checksum = hashlib.sha256(content + str(report_id).encode()).hexdigest()
    created_at = datetime.now(UTC)

    # --- parse sub-stages (CPU) ---
    t0 = time.perf_counter()
    df = load_file_to_dataframe("large_wb_test.xlsx", content)
    wall["load_excel"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    _parser, normalized_rows = parse_wb_report(df)
    wall["parse_normalize"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    wb_result = WbFinancialProcessor.process(
        report_id=report_id,
        report_created_at=created_at,
        filename="large_wb_test.xlsx",
        content=content,
    )
    wall["process_total_cpu"] = time.perf_counter() - t0

    affected_dates = len({item.aggregate_date for item in wb_result.daily_aggregates})
    sku_per_day_estimate = len(wb_result.sku_daily_metrics) / max(affected_dates, 1)

    user = User(
        id=user_id,
        email=f"profile-{user_id}@example.com",
        hashed_password="profile",
        is_active=True,
    )
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="large_wb_test.xlsx",
        file_path=STORAGE_PATH,
        file_checksum=file_checksum,
    )

    persist_timings: dict[str, float] = {}
    ai_context_s = 0.0
    ack_s = 0.0

    async with SessionLocal() as db:
        async with db.begin():
            db.add(user)
            await db.flush()

        async with TenantSession.transaction(db, user_id):
            db.add(report)
            await db.flush()

            token = _set_stage("enrich_with_costs")
            t0 = time.perf_counter()
            costs = await WbFinancialPersistService.load_cost_snapshots(db, user_id)
            wb_enriched = WbFinancialProcessor.enrich_with_costs(wb_result, costs)
            wall["enrich_with_costs"] = time.perf_counter() - t0
            _reset_stage(token)

            persist_timings = await profile_persist_stages(
                db, user, report, wb_enriched, profiler
            )

            pipeline = ETLPipeline(db, user_id)
            token = _set_stage("ai_context")
            t0 = time.perf_counter()
            await pipeline._prepare_ai_context_idempotent(
                report,
                dict(wb_enriched.analytics_payload),
                job_id=uuid4(),
                in_transaction=True,
            )
            ai_context_s = time.perf_counter() - t0
            _reset_stage(token)

            token = _set_stage("persist_business_result")
            t0 = time.perf_counter()
            report_service = ReportService(db, user)
            await report_service.persist_business_result(
                report,
                raw_data=dict(wb_enriched.raw_snapshot),
                row_count=wb_enriched.row_count,
                in_transaction=True,
            )
            wall["persist_business_result"] = time.perf_counter() - t0
            _reset_stage(token)

        # cleanup
        async with TenantSession.transaction(db, user_id):
            await db.execute(delete(Report).where(Report.id == report_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.flush()

    wall["total"] = time.perf_counter() - total_t0

    # Aggregate SQL stats into report buckets
    buckets = {
        "persist_layers": ["persist_layers", "opening_balance_validation"],
        "inventory_rebuild": ["inventory_rebuild"],
        "rebuild_aggregates": ["rebuild_aggregates"],
        "ai_context": ["ai_context", "enrich_with_costs", "persist_business_result"],
        "other": [],
    }
    assigned = set()
    bucket_stats: dict[str, StageSqlStats] = {}
    for bucket, stages in buckets.items():
        agg = StageSqlStats()
        for st in stages:
            if st in profiler.stages:
                s = profiler.stages[st]
                agg.count += s.count
                agg.total_ms += s.total_ms
                assigned.add(st)
        bucket_stats[bucket] = agg
    other = StageSqlStats()
    for st, s in profiler.stages.items():
        if st not in assigned:
            other.count += s.count
            other.total_ms += s.total_ms
    bucket_stats["other"] = other

    total_sql = sum(s.count for s in profiler.stages.values())
    total_sql_ms = sum(s.total_ms for s in profiler.stages.values())

    # Top expensive statement patterns
    all_queries: list[tuple[str, float, str]] = []
    for stage, stats in profiler.stages.items():
        for stmt in stats.statements:
            all_queries.append((stage, stats.avg_ms, stmt))

    result = {
        "file": {
            "name": "large_wb_test.xlsx",
            "size_mb": round(file_mb, 2),
            "rows": wb_result.row_count,
            "normalized_rows": len(wb_result.normalized_rows),
            "ledger_entries": len(wb_result.ledger_entries),
            "affected_dates": affected_dates,
            "sku_metrics_total": len(wb_result.sku_daily_metrics),
            "sku_per_day_avg": round(sku_per_day_estimate, 1),
        },
        "wall_seconds": {
            "read_report_file": round(wall["read_report_file"], 3),
            "load_excel": round(wall["load_excel"], 3),
            "parse_normalize": round(wall["parse_normalize"], 3),
            "process_total_cpu": round(wall["process_total_cpu"], 3),
            "enrich_with_costs": round(wall.get("enrich_with_costs", 0), 3),
            "opening_balance_validation": round(persist_timings.get("opening_balance_validation", 0), 3),
            "persist_layers": round(persist_timings.get("persist_layers", 0), 3),
            "inventory_rebuild": round(persist_timings.get("inventory_rebuild", 0), 3),
            "rebuild_aggregates": round(persist_timings.get("rebuild_aggregates", 0), 3),
            "ai_context": round(ai_context_s, 3),
            "persist_business_result": round(wall.get("persist_business_result", 0), 3),
            "total": round(wall["total"], 3),
        },
        "sql_by_stage_tag": {
            stage: {"count": s.count, "total_ms": round(s.total_ms, 1), "avg_ms": round(s.avg_ms, 2)}
            for stage, s in sorted(profiler.stages.items(), key=lambda x: -x[1].total_ms)
        },
        "sql_by_bucket": {
            bucket: {
                "count": s.count,
                "total_ms": round(s.total_ms, 1),
                "avg_ms": round(s.avg_ms, 2),
            }
            for bucket, s in bucket_stats.items()
        },
        "sql_totals": {
            "total_queries": total_sql,
            "total_ms": round(total_sql_ms, 1),
            "avg_ms": round(total_sql_ms / total_sql, 2) if total_sql else 0,
        },
        "n_plus_one_estimate": {
            "dates": affected_dates,
            "expected_ledger_reads_per_date": 3,
            "expected_cost_reads_per_date": 3,
            "expected_sku_upserts": len(wb_result.sku_daily_metrics),
            "expected_unit_econ_upserts": len(
                {m.sku for m in wb_result.sku_daily_metrics if m.sku}
            )
            * affected_dates
            // max(affected_dates, 1),
            "theoretical_min_queries_aggregates": (
                affected_dates * 6 + len(wb_result.sku_daily_metrics) * 2
            ),
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
