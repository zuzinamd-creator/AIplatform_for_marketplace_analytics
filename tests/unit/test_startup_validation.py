"""Startup validation warnings for local runtime."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.core.startup_validation import validate_environment


def _settings(**overrides: object) -> SimpleNamespace:
    base = {
        "debug": False,
        "maintenance_mode": False,
        "secret_key": "long-enough-secret",
        "environment_mode": "LOCAL_DEV",
        "database_url": "postgresql://localhost/db",
        "ai_enabled": True,
        "ai_provider": "mock",
        "ai_openai_api_key": "",
        "ai_prompt_runtime_version": "v3",
        "storage_backend": "local",
        "supabase_url": "",
        "allow_local_storage_fallback": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@contextmanager
def _patch_settings(**overrides: object):
    s = _settings(**overrides)
    with (
        patch("app.core.startup_validation.settings", s),
        patch("app.core.environment.settings", s),
    ):
        yield s


def test_warn_mock_provider_with_api_key() -> None:
    with _patch_settings(ai_provider="mock", ai_openai_api_key="sk-test"):
        report = validate_environment()
    assert report.ok
    assert any("AI_OPENAI_API_KEY" in w for w in report.warnings)


def test_warn_real_provider_without_key() -> None:
    with _patch_settings(ai_provider="openai", ai_openai_api_key=""):
        report = validate_environment()
    assert report.ok
    assert any("AI_OPENAI_API_KEY is empty" in w for w in report.warnings)


def test_main_requires_ssl_and_persistent_db() -> None:
    with _patch_settings(
        environment_mode="MAIN",
        database_url="postgresql+asyncpg://postgres:pw@localhost:5432/postgres",
        storage_backend="supabase",
        allow_local_storage_fallback=False,
    ):
        report = validate_environment()
    assert not report.ok
    assert any("SSL" in e for e in report.errors)
    assert any("persistent cloud" in e for e in report.errors)


def test_main_supabase_with_ssl_ok() -> None:
    with _patch_settings(
        environment_mode="MAIN",
        database_url=(
            "postgresql+asyncpg://postgres:pw@db.abc.supabase.co:5432/postgres?ssl=require"
        ),
        storage_backend="supabase",
        allow_local_storage_fallback=False,
    ):
        report = validate_environment()
    assert report.ok


def test_main_rejects_pooler_host() -> None:
    with _patch_settings(
        environment_mode="MAIN",
        database_url=(
            "postgresql+asyncpg://postgres.ref:pw@aws-0-eu-west-1.pooler.supabase.com:5432/"
            "postgres?ssl=require"
        ),
        storage_backend="supabase",
        allow_local_storage_fallback=False,
    ):
        report = validate_environment()
    assert not report.ok
    assert any("Session Pooler" in e for e in report.errors)


def test_main_rejects_non_direct_supabase_host() -> None:
    with _patch_settings(
        environment_mode="MAIN",
        database_url=(
            "postgresql+asyncpg://postgres:pw@custom.postgres.example.com:5432/postgres?ssl=require"
        ),
        storage_backend="supabase",
        allow_local_storage_fallback=False,
    ):
        report = validate_environment()
    assert not report.ok
    assert any("db.<project-ref>.supabase.co" in e for e in report.errors)
