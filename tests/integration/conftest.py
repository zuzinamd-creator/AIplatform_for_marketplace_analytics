"""Shared fixtures for PostgreSQL integration tests."""

from __future__ import annotations

import hashlib
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.db_isolation import truncate_integration_tables

TESTS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INTEGRATION_DB = "postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test"


@pytest.fixture(autouse=True)
def _patch_session_local_for_integration(
    db_engine, integration_enabled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Route app.core.database.SessionLocal to the integration test engine."""
    if not integration_enabled:
        return
    test_session_local = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr("app.core.database.SessionLocal", test_session_local)


@pytest.fixture(autouse=True)
async def _integration_db_isolated(
    db_engine, integration_enabled: bool
) -> AsyncGenerator[None, None]:
    """TRUNCATE tenant/queue tables before and after each integration test."""
    if not integration_enabled:
        yield
        return
    await truncate_integration_tables(db_engine)
    yield
    await truncate_integration_tables(db_engine)


@pytest.fixture
def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


def wb_weekly_report_path() -> Path:
    """Single trimmed WB weekly report under tests/ (encoding-safe discovery)."""
    matches = sorted(TESTS_DIR.glob("*.xlsx"))
    if not matches:
        pytest.fail(
            f"No .xlsx test file in {TESTS_DIR}. "
            "Place 'Еженедельный детализированный отчет WB.xlsx' in tests/."
        )
    if len(matches) > 1:
        wb_named = [path for path in matches if "WB" in path.name or "wb" in path.name.lower()]
        if len(wb_named) == 1:
            return wb_named[0]
    return matches[0]


@pytest.fixture
def wb_weekly_report_file() -> Path:
    path = wb_weekly_report_path()
    if not path.is_file():
        pytest.fail(f"WB weekly report not found: {path}")
    return path


@pytest.fixture
def wb_weekly_report_bytes(wb_weekly_report_file: Path) -> bytes:
    return wb_weekly_report_file.read_bytes()


@pytest.fixture
def wb_weekly_report_checksum(wb_weekly_report_bytes: bytes) -> str:
    return hashlib.sha256(wb_weekly_report_bytes).hexdigest()


@pytest.fixture
async def integration_user(db_session: AsyncSession) -> AsyncGenerator[User, None]:
    user = User(
        id=uuid4(),
        email=f"integration-{uuid4()}@example.com",
        hashed_password="test-hash",
        is_active=True,
    )
    async with db_session.begin():
        db_session.add(user)
        await db_session.flush()
    yield user


@pytest.fixture
def make_wb_report(
    integration_user: User,
    wb_weekly_report_file: Path,
    wb_weekly_report_checksum: str,
):
    def _factory(*, checksum: str | None = None) -> Report:
        return Report(
            id=uuid4(),
            user_id=integration_user.id,
            marketplace=Marketplace.WILDBERRIES,
            report_type=ReportType.SALES,
            original_filename=wb_weekly_report_file.name,
            file_path=f"reports/{wb_weekly_report_file.name}",
            file_checksum=checksum or wb_weekly_report_checksum,
            status=ReportStatus.PROCESSING,
        )

    return _factory
