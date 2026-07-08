"""Unit tests for app.ops.preflight."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.startup_validation import StartupValidationReport
from app.ops.preflight import (
    build_preflight_report,
    check_alembic_revision,
    collect_required_field_errors,
    run_preflight,
)


@contextmanager
def _patch_settings(**overrides: object):
    base = {
        "database_url": "postgresql+asyncpg://u:p@db.abc.supabase.co:5432/postgres?ssl=require",
        "secret_key": "long-enough-production-secret",
        "environment_mode": "MAIN",
        "supabase_url": "https://abc.supabase.co",
    }
    base.update(overrides)
    settings = SimpleNamespace(**base)
    with patch("app.ops.preflight.settings", settings):
        yield settings


def test_collect_required_fields_ok_main() -> None:
    with _patch_settings():
        assert collect_required_field_errors() == []


def test_collect_required_missing_database_url() -> None:
    with _patch_settings(database_url=""):
        errors = collect_required_field_errors()
    assert any("DATABASE_URL" in e for e in errors)


def test_collect_required_missing_secret_key() -> None:
    with _patch_settings(secret_key=""):
        errors = collect_required_field_errors()
    assert any("SECRET_KEY" in e for e in errors)


def test_collect_required_missing_environment_mode() -> None:
    with _patch_settings(environment_mode=""):
        errors = collect_required_field_errors()
    assert any("ENVIRONMENT_MODE" in e for e in errors)


def test_collect_required_supabase_url_for_main() -> None:
    with _patch_settings(supabase_url=""):
        errors = collect_required_field_errors()
    assert any("SUPABASE_URL" in e for e in errors)


def test_collect_required_supabase_not_required_for_local_dev() -> None:
    with _patch_settings(environment_mode="LOCAL_DEV", supabase_url=""):
        errors = collect_required_field_errors()
    assert not any("SUPABASE_URL" in e for e in errors)


def test_build_preflight_merges_startup_errors() -> None:
    env_report = StartupValidationReport(
        ok=False,
        warnings=("warn",),
        errors=("startup error",),
    )
    with _patch_settings():
        report = build_preflight_report(env_report)
    assert not report.ok
    assert "startup error" in report.errors


def test_run_preflight_success() -> None:
    ok_report = StartupValidationReport(ok=True, warnings=(), errors=())
    with (
        _patch_settings(),
        patch("app.ops.preflight.build_preflight_report", return_value=ok_report),
    ):
        assert run_preflight() == 0


def test_run_preflight_failure() -> None:
    bad_report = StartupValidationReport(ok=False, warnings=(), errors=("bad",))
    with patch("app.ops.preflight.build_preflight_report", return_value=bad_report):
        assert run_preflight() == 1


def test_run_preflight_schema_mismatch() -> None:
    ok_report = StartupValidationReport(ok=True, warnings=(), errors=())
    with (
        _patch_settings(),
        patch("app.ops.preflight.build_preflight_report", return_value=ok_report),
        patch(
            "app.ops.preflight.check_alembic_revision",
            new_callable=AsyncMock,
            return_value=(False, "schema drift: code head=0034 db=0033"),
        ),
    ):
        assert run_preflight(check_schema=True) == 1


@pytest.mark.asyncio
async def test_check_alembic_revision_match() -> None:
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = "0033_report_promotion_expenses"
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_engine = MagicMock()

    async def _dispose() -> None:
        return None

    mock_engine.dispose = AsyncMock(side_effect=_dispose)

    class _Ctx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            return None

    mock_engine.connect.return_value = _Ctx()

    with (
        patch("app.ops.preflight._alembic_head_revision", return_value="0033_report_promotion_expenses"),
        patch("app.ops.preflight.create_async_engine", return_value=mock_engine),
    ):
        ok, detail = await check_alembic_revision()
    assert ok is True
    assert detail == "0033_report_promotion_expenses"


@pytest.mark.asyncio
async def test_check_alembic_revision_drift() -> None:
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = "0033_report_promotion_expenses"
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_engine = MagicMock()

    class _Ctx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            return None

    mock_engine.connect.return_value = _Ctx()
    mock_engine.dispose = AsyncMock()

    with (
        patch("app.ops.preflight._alembic_head_revision", return_value="0034_invite_only_admin_access"),
        patch("app.ops.preflight.create_async_engine", return_value=mock_engine),
    ):
        ok, detail = await check_alembic_revision()
    assert ok is False
    assert "schema drift" in detail
