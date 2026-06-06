"""Regression: tenant reports remain visible via list API after persistence."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security import create_access_token
from app.core.security_context import TenantSession
from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from httpx import AsyncClient


@pytest.mark.integration
async def test_uploaded_report_survives_list_api(
    api_client: AsyncClient,
    session_factory,
) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"reports-{user_id}@example.com",
        hashed_password="not-used",
        is_active=True,
    )
    report_id = uuid4()
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}

    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()

        async with TenantSession.transaction(session, user.id):
            session.add(
                Report(
                    id=report_id,
                    user_id=user.id,
                    marketplace=Marketplace.WILDBERRIES,
                    report_type=ReportType.FINANCE,
                    original_filename="weekly.xlsx",
                    file_path=f"{user.id}/{report_id}/weekly.xlsx",
                    file_checksum=f"chk-{report_id}",
                )
            )
            session.add(
                EtlJob(
                    id=uuid4(),
                    user_id=user.id,
                    report_id=report_id,
                    idempotency_key=f"chk-{report_id}",
                    file_path=f"{user.id}/{report_id}/weekly.xlsx",
                    marketplace=Marketplace.WILDBERRIES,
                    report_type=ReportType.FINANCE,
                    status=JobStatus.COMPLETED,
                    attempt_count=1,
                    max_attempts=3,
                )
            )
            await session.flush()

    listed = await api_client.get("/api/v1/reports", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["id"] == str(report_id)
    assert body[0]["status"] == "processed"

    integrity = await api_client.get("/api/v1/system/data-integrity", headers=headers)
    assert integrity.status_code == 200
    payload = integrity.json()
    assert payload["healthy"] is True
    assert payload["total_reports"] == 1
