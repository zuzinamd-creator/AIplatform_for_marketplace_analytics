#!/usr/bin/env python3
"""Per-subsystem timing for GET /dashboard/summary."""

from __future__ import annotations

import asyncio
import os
import time
from datetime import date
from pathlib import Path
from uuid import UUID

from app.core.database import SessionLocal
from app.models.report import Marketplace
from app.models.user import User
from app.services.ai_service import AIService
from app.services.analytics_service import AnalyticsService, Period
from app.services.ops_service import OpsService


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


async def _run(label: str, fn) -> None:
    start = time.perf_counter()
    async with SessionLocal() as db:
        await fn(db)
    print(f"{label:36s} {(time.perf_counter() - start) * 1000:8.1f} ms")


async def main() -> None:
    _load_env()
    default_test_id = os.environ.get("MVP_TEST_USER_ID", "c4fcd1f7-b315-4ade-bfa1-e804d69ab680")
    user_id = UUID(os.environ.get("PROFILE_USER_ID", default_test_id))
    marketplace = Marketplace.WILDBERRIES
    period = Period(start=date(2025, 1, 1), end=date(2025, 12, 31))

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None:
            raise SystemExit(f"User not found: {user_id}")
        print(f"tenant={user.email} period={period.start}..{period.end}")
        print()

    tasks = [
        ("ops.queue", lambda db: OpsService(db, user).list_queue_jobs(skip=0, limit=10)),
        ("ops.runtime_summary", lambda db: OpsService(db, user).runtime_summary()),
        ("ai.operational_status", lambda db: AIService(db, user.id).operational_status()),
        ("ai.todays_focus", lambda db: AIService(db, user.id).todays_focus()),
        ("ai.recommendations", lambda db: AIService(db, user.id).list_recommendations(skip=0, limit=5)),
        (
            "analytics.revenue_summary",
            lambda db: AnalyticsService(db, user).revenue_summary(marketplace=marketplace, period=period),
        ),
        (
            "analytics.revenue_trend",
            lambda db: AnalyticsService(db, user).revenue_trend(marketplace=marketplace, period=period),
        ),
        (
            "analytics.financial_summary",
            lambda db: AnalyticsService(db, user).financial_summary(marketplace=marketplace, period=period),
        ),
        (
            "analytics.financial_trends",
            lambda db: AnalyticsService(db, user).financial_trends(marketplace=marketplace, period=period),
        ),
        (
            "analytics.top_skus",
            lambda db: AnalyticsService(db, user).top_skus(
                marketplace=marketplace, period=period, limit=5, sort="revenue"
            ),
        ),
        ("analytics.coverage", lambda db: AnalyticsService(db, user).coverage()),
    ]

    results: list[tuple[str, float]] = []
    for label, fn in tasks:
        start = time.perf_counter()
        async with SessionLocal() as db:
            await fn(db)
        elapsed = (time.perf_counter() - start) * 1000
        results.append((label, elapsed))
        print(f"{label:36s} {elapsed:8.1f} ms")

    print()
    results.sort(key=lambda item: item[1], reverse=True)
    print("Top 5 expensive:")
    for label, elapsed in results[:5]:
        print(f"  {label}: {elapsed:.0f} ms")

    async def parallel() -> None:
        async def one(fn) -> None:
            async with SessionLocal() as db:
                await fn(db)

        await asyncio.gather(*(one(fn) for _, fn in tasks))

    t0 = time.perf_counter()
    await parallel()
    print(f"\nparallel wall-clock (11 sessions): {(time.perf_counter() - t0) * 1000:.0f} ms")


if __name__ == "__main__":
    asyncio.run(main())
