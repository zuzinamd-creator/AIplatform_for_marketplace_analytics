from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.finance.cost_lookup import unit_cost_on_date
from app.domain.finance.types import SkuCostSnapshot
from app.models.cost_history import CostHistory
from app.services.cost_service import CostService


def test_unit_cost_falls_back_after_deleting_later_record() -> None:
    """Jan 100 → Feb 5000 (deleted) → Feb sale uses Jan cost again."""
    history = [
        SkuCostSnapshot(
            sku="SKU-A",
            effective_from=date(2026, 1, 1),
            product_cost=Decimal("100"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
        ),
    ]
    assert unit_cost_on_date(history, date(2026, 2, 15)) == Decimal("100")


@pytest.mark.asyncio
async def test_delete_cost_triggers_projection_rebuild() -> None:
    user_id = uuid4()
    cost_id = uuid4()
    row = CostHistory(
        id=cost_id,
        user_id=user_id,
        internal_sku="SKU-A",
        product_cost=Decimal("5000"),
        packaging_cost=Decimal("0"),
        inbound_logistics_cost=Decimal("0"),
        additional_cost=Decimal("0"),
        cost=Decimal("5000"),
        currency="RUB",
        effective_from=date(2026, 2, 1),
    )
    db = AsyncMock()
    service = CostService(db, MagicMock(id=user_id))
    service.user = MagicMock(id=user_id)

    tx_mock = AsyncMock()
    tx_mock.__aenter__ = AsyncMock(return_value=None)
    tx_mock.__aexit__ = AsyncMock(return_value=None)

    with patch.object(service, "get_cost", AsyncMock(return_value=row)):
        with patch.object(service, "_rls_transaction", return_value=tx_mock):
            with patch.object(service, "_refresh_financial_projections", AsyncMock()) as refresh_mock:
                await service.delete_cost(cost_id)

    db.delete.assert_called_once_with(row)
    refresh_mock.assert_awaited_once()
