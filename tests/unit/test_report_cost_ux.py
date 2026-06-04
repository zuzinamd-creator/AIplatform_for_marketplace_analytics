"""Unit tests for seller UX: report periods and cost listing."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.report import Marketplace, Report, ReportType
from app.schemas.report_mappers import report_to_response
from app.services.cost_service import CostService


def test_report_to_response_includes_period_from_mapper() -> None:
    now = datetime.now(UTC)
    report = Report(
        id=uuid4(),
        user_id=uuid4(),
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.FINANCE,
        original_filename="wb.xlsx",
        file_path="/x",
        file_checksum="abc",
        raw_data={"period_start": "2025-01-01", "period_end": "2025-01-31"},
        created_at=now,
        updated_at=now,
    )
    resp = report_to_response(report, None, period_start=date(2025, 2, 1), period_end=date(2025, 2, 28))
    assert resp.period_start == date(2025, 2, 1)
    assert resp.period_end == date(2025, 2, 28)


def test_cost_as_of_picks_latest_row_per_sku() -> None:
    rows = [
        _fake_cost("SKU-A", date(2025, 1, 1), "10"),
        _fake_cost("SKU-A", date(2025, 2, 1), "20"),
        _fake_cost("SKU-B", date(2025, 1, 15), "5"),
    ]
    latest = CostService.filter_costs_as_of(rows, date(2025, 2, 15))
    by_sku = {r.internal_sku: r for r in latest}
    assert by_sku["SKU-A"].product_cost == Decimal("20")
    assert by_sku["SKU-B"].product_cost == Decimal("5")


def _fake_cost(sku: str, effective_from: date, product_cost: str):
    from app.models.cost_history import CostHistory

    return CostHistory(
        id=uuid4(),
        user_id=uuid4(),
        internal_sku=sku,
        product_cost=Decimal(product_cost),
        packaging_cost=Decimal("0"),
        inbound_logistics_cost=Decimal("0"),
        additional_cost=Decimal("0"),
        cost=Decimal(product_cost),
        currency="RUB",
        effective_from=effective_from,
        effective_to=None,
    )
