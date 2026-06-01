"""Integration tests for enterprise runtime ops APIs."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.models.user import User
from app.services.ops_service import OpsService


async def _create_user(session, user_id: UUID) -> User:
    user = User(
        id=user_id,
        email=f"ent-ops-{user_id}@example.com",
        hashed_password="x",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.mark.integration
async def test_operational_simulation_dry_run(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        user = await _create_user(session, user_id)
        svc = OpsService(session, user)

        status = await svc.autonomy_status()
        assert status.safety_level in ("off", "monitor", "limited", "standard")

        sim = await svc.run_simulation("full_cycle")
        assert sim.dry_run is True
        assert sim.forecast.overload_risk >= 0


@pytest.mark.integration
async def test_operational_forecast_tenant(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        user = await _create_user(session, user_id)
        forecast = await OpsService(session, user).operational_forecast()
        assert forecast.autonomy_health_score >= 0
