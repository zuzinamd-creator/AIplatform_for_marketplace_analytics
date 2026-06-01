"""PostgreSQL cleanup for deterministic integration tests."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Tenant-scoped / queue data — truncated each test. Global semantics registry is kept.
INTEGRATION_TRUNCATE_TABLES: tuple[str, ...] = (
    "etl_anomalies",
    "inventory_integrity_anomalies",
    "snapshot_consistency_checks",
    "warehouse_stock_snapshots_staging",
    "warehouse_stock_snapshots",
    "inventory_ledger_entries",
    "snapshot_rebuild_requirements",
    "financial_ledger_entries",
    "normalized_report_rows",
    "raw_reports",
    "report_reconciliations",
    "daily_aggregates",
    "sku_daily_metrics",
    "runtime_autonomous_actions",
    "runtime_schedule_policies",
    "runtime_autonomy_events",
    "runtime_process_heartbeats",
    "runtime_process_leases",
    "tenant_containment_states",
    "operator_audit_events",
    "ai_session_turns",
    "ai_recommendation_feedback",
    "ai_recommendations",
    "ai_strategic_memory",
    "ai_execution_runs",
    "ai_insights",
    "etl_jobs",
    "reports",
    "cost_history",
    "metrics",
    "products",
    "sku_mapping",
    "users",
)


async def truncate_integration_tables(engine: AsyncEngine) -> None:
    """Remove tenant/queue rows; skips tables not yet migrated (e.g. ai_execution_runs)."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        )
        existing = {row[0] for row in result}
        tables = [name for name in INTEGRATION_TRUNCATE_TABLES if name in existing]
        if not tables:
            return
        sql = f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"
        await conn.execute(text(sql))
