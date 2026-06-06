#!/usr/bin/env python3
"""Collect post-audit evidence: SKU scan, E2E WB file, AI payload sample."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.parsers.wb.header_detection import locate_wb_table
from app.parsers.wb.streaming import iter_wb_normalized_rows
from app.parsers.wb.base import resolve_column_map
from app.models.report import Marketplace
from app.services.ai_service import AIService
from app.ai.grounding.assembler import build_grounded_context
from app.core.tenant_context import set_current_user_context, set_bypass_rls_context


def load_env() -> None:
    env = ROOT / ".env"
    for line in env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


async def scan_test_skus(admin_url: str) -> dict:
    engine = create_async_engine(admin_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    tables = [
        ("products", "internal_sku"),
        ("cost_history", "internal_sku"),
        ("sku_daily_metrics", "sku"),
        ("sku_unit_economics_daily", "sku"),
        ("financial_ledger_entries", "sku"),
    ]
    patterns = ["SKU-001", "SKU-002", "SKU-003", "SKU-00%"]
    out: dict[str, dict[str, int]] = {}
    async with Session() as db:
        for table, col in tables:
            out[table] = {}
            for pat in patterns:
                if pat.endswith("%"):
                    q = text(f"SELECT count(*) FROM {table} WHERE {col} ILIKE :p")
                    n = (await db.execute(q, {"p": pat})).scalar()
                else:
                    q = text(f"SELECT count(*) FROM {table} WHERE {col} = :p")
                    n = (await db.execute(q, {"p": pat})).scalar()
                out[table][pat] = int(n or 0)
        out["ai_insights"] = {
            "context_sku001": int(
                (
                    await db.execute(
                        text(
                            "SELECT count(*) FROM ai_insights WHERE context_payload::text ILIKE '%SKU-001%'"
                        )
                    )
                ).scalar()
                or 0
            )
        }
        out["reports"] = {
            "raw_sku001": int(
                (
                    await db.execute(
                        text("SELECT count(*) FROM reports WHERE raw_data::text ILIKE '%SKU-001%'")
                    )
                ).scalar()
                or 0
            )
        }
    await engine.dispose()
    return out


def e2e_wb_file(path: Path) -> dict:
    located = locate_wb_table(path, filename=path.name)
    total = sum(len(chunk) for _, chunk in iter_wb_normalized_rows(path, filename=path.name))
    skus = set()
    dates = []
    for _, chunk in iter_wb_normalized_rows(path, filename=path.name):
        for row in chunk:
            if row.sku:
                skus.add(row.sku)
            if row.operation_date:
                dates.append(row.operation_date)
    return {
        "file": str(path),
        "sheet_name": located.sheet_name,
        "header_row_index": located.header_row_index,
        "headers_sample": located.headers[:8],
        "operation_date_column": resolve_column_map(located.headers).get("operation_date"),
        "row_count": total,
        "sku_count": len(skus),
        "period_start": min(dates).isoformat() if dates else None,
        "period_end": max(dates).isoformat() if dates else None,
        "sku_sample": sorted(skus)[:5],
    }


async def sample_ai_payload(admin_url: str) -> dict | None:
    engine = create_async_engine(admin_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT id, email FROM users WHERE email NOT LIKE 'rls-proof-%' ORDER BY created_at DESC LIMIT 1"
                )
            )
        ).one_or_none()
        if not row:
            await engine.dispose()
            return None
        user_id, email = row
        await set_bypass_rls_context(db, True)
        await set_current_user_context(db, user_id)
        svc = AIService(db, user_id)
        end = date.today()
        start = end - timedelta(days=30)
        insight = await svc._insight_input_for_period(
            marketplace=Marketplace.WILDBERRIES,
            period_start=start,
            period_end=end,
        )
        if insight is None:
            await engine.dispose()
            return {"user": email, "payload": None}
        grounded = build_grounded_context(
            insight_input=insight,
            semantics_version="1.0",
            workflow="revenue_insight",
            rebuild_pending_count=0,
            rebuild_running_count=0,
            degraded_mode=False,
        )
        payload = {
            "user": email,
            "metrics_snapshot": grounded.metrics_snapshot,
            "evidence": [e.model_dump() for e in grounded.evidence],
            "degraded_mode": grounded.degraded_mode,
            "freshness_note": grounded.freshness_note,
        }
    await engine.dispose()
    return payload


async def main() -> None:
    load_env()
    admin_url = os.environ.get("ALEMBIC_DATABASE_URL", os.environ["DATABASE_URL"])
    fixture = ROOT / "tests/Еженедельный детализированный отчет WB.xlsx"
    result = {
        "sku_scan": await scan_test_skus(admin_url),
        "wb_e2e": e2e_wb_file(fixture) if fixture.is_file() else None,
        "ai_payload_sample": await sample_ai_payload(admin_url),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
