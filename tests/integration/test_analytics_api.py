"""Analytics read API integration tests (tenant-scoped, read-only)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.security import create_access_token
from app.core.security_context import TenantSession
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.inventory.snapshot import WarehouseStockSnapshot
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from httpx import AsyncClient


@pytest.mark.integration
async def test_analytics_kpis_endpoints(
    api_client: AsyncClient,
    session_factory,
) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"analytics-{user_id}@example.com",
        hashed_password="not-used",
        is_active=True,
    )
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}

    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()

        async with TenantSession.transaction(session, user.id):
            session.add_all(
                [
                    Report(
                        id=uuid4(),
                        user_id=user.id,
                        marketplace=Marketplace.WILDBERRIES,
                        report_type=ReportType.FINANCE,
                        original_filename="wb_finance.xlsx",
                        file_checksum="chk-1",
                    ),
                    Report(
                        id=uuid4(),
                        user_id=user.id,
                        marketplace=Marketplace.COSTS,
                        report_type=ReportType.COSTS,
                        original_filename="costs.xlsx",
                        file_checksum="chk-2",
                    ),
                ]
            )
            session.add_all(
                [
                    DailyAggregate(
                        user_id=user.id,
                        aggregate_date=date(2026, 1, 10),
                        marketplace=Marketplace.WILDBERRIES,
                        revenue=Decimal("1000"),
                        net_profit=Decimal("200"),
                        margin=Decimal("20"),
                        units_sold=10,
                    ),
                    DailyAggregate(
                        user_id=user.id,
                        aggregate_date=date(2026, 1, 11),
                        marketplace=Marketplace.WILDBERRIES,
                        revenue=Decimal("500"),
                        net_profit=Decimal("50"),
                        margin=Decimal("10"),
                        units_sold=5,
                    ),
                ]
            )
            session.add_all(
                [
                    SkuDailyMetric(
                        user_id=user.id,
                        sku="SKU-1",
                        metric_date=date(2026, 1, 10),
                        marketplace=Marketplace.WILDBERRIES,
                        revenue=Decimal("600"),
                        net_profit=Decimal("120"),
                        margin=Decimal("20"),
                        units_sold=6,
                    ),
                    SkuDailyMetric(
                        user_id=user.id,
                        sku="SKU-2",
                        metric_date=date(2026, 1, 10),
                        marketplace=Marketplace.WILDBERRIES,
                        revenue=Decimal("400"),
                        net_profit=Decimal("80"),
                        margin=Decimal("20"),
                        units_sold=4,
                    ),
                ]
            )
            session.add(
                WarehouseStockSnapshot(
                    user_id=user.id,
                    snapshot_date=date(2026, 1, 11),
                    sku="SKU-1",
                    nm_id="NM-1",
                    warehouse_name="WH-1",
                    opening_stock=10,
                    inbound_units=2,
                    sold_units=3,
                    returned_units=0,
                    lost_units=1,
                    writeoff_units=0,
                    expected_closing_stock=8,
                    actual_stock=7,
                    discrepancy_units=-1,
                    discrepancy_cost=Decimal("50"),
                    discrepancy_sale_value=Decimal("120"),
                    semantics_version="1.0",
                )
            )

    summary = await api_client.get(
        "/api/v1/analytics/kpis/summary",
        params={"marketplace": "wildberries", "start": "2026-01-10", "end": "2026-01-11"},
        headers=headers,
    )
    assert summary.status_code == 200
    body = summary.json()
    # API serializes decimals as strings; formatting may include fixed scale.
    assert Decimal(body["kpis"]["total_revenue"]) == Decimal("1500")

    trend = await api_client.get(
        "/api/v1/analytics/kpis/trends/daily",
        params={"marketplace": "wildberries", "start": "2026-01-10", "end": "2026-01-11"},
        headers=headers,
    )
    assert trend.status_code == 200
    assert len(trend.json()["points"]) == 2

    top = await api_client.get(
        "/api/v1/analytics/kpis/top-skus",
        params={
            "marketplace": "wildberries",
            "start": "2026-01-10",
            "end": "2026-01-11",
            "limit": 10,
            "sort": "revenue",
        },
        headers=headers,
    )
    assert top.status_code == 200
    assert top.json()["items"][0]["sku"] == "SKU-1"

    abc = await api_client.get(
        "/api/v1/analytics/kpis/abc",
        params={"marketplace": "wildberries", "start": "2026-01-10", "end": "2026-01-11"},
        headers=headers,
    )
    assert abc.status_code == 200
    assert {b["bucket"] for b in abc.json()["buckets"]} == {"A", "B", "C"}

    wh = await api_client.get(
        "/api/v1/analytics/kpis/warehouses",
        params={"snapshot_date": "2026-01-11", "semantics_version": "1.0"},
        headers=headers,
    )
    assert wh.status_code == 200
    assert wh.json()["items"][0]["warehouse_name"] == "WH-1"

    risk = await api_client.get(
        "/api/v1/analytics/kpis/inventory-risk",
        params={"snapshot_date": "2026-01-11", "semantics_version": "1.0"},
        headers=headers,
    )
    assert risk.status_code == 200
    assert Decimal(risk.json()["discrepancy_cost_total"]) == Decimal("50")

    coverage = await api_client.get("/api/v1/analytics/coverage", headers=headers)
    assert coverage.status_code == 200
    cov = coverage.json()
    assert "freshness" in cov
    assert "uploaded_report_types" in cov

