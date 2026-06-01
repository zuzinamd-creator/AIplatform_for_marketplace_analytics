"""asyncpg SSL connect_args for Supabase / managed Postgres."""

from __future__ import annotations

import ssl
from unittest.mock import patch

from sqlalchemy.engine import make_url

from app.core.asyncpg_connect import (
    asyncpg_connect_args,
    build_verified_ssl_context,
    database_url_requires_ssl,
    format_database_url_for_env,
    password_needs_url_encoding,
    resolve_database_url,
    sqlalchemy_async_database_url,
)


def test_database_url_requires_ssl() -> None:
    assert database_url_requires_ssl("postgresql://h/db?ssl=require")
    assert database_url_requires_ssl("postgresql://h/db?sslmode=require")
    assert not database_url_requires_ssl("postgresql://localhost/db")


def test_verified_ssl_context_uses_certifi() -> None:
    ctx = build_verified_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_direct_supabase_url_gets_strict_ssl() -> None:
    url = "postgresql+asyncpg://u:p@db.abc.supabase.co:5432/postgres?ssl=require"
    args = asyncpg_connect_args(url)
    assert args["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert "statement_cache_size" not in args


def test_local_url_no_ssl_context() -> None:
    args = asyncpg_connect_args("postgresql+asyncpg://postgres:pw@localhost:5432/marketplace")
    assert "ssl" not in args


def test_sqlalchemy_url_strips_ssl_query() -> None:
    raw = "postgresql+asyncpg://u:p@host:5432/db?ssl=require&connect_timeout=10"
    cleaned = sqlalchemy_async_database_url(raw)
    assert "ssl=require" not in cleaned
    assert "connect_timeout" in cleaned


def test_resolve_database_url_encodes_special_password() -> None:
    raw = format_database_url_for_env(
        project_ref="ref",
        password="p@ss:word",
        region="eu-west-1",
    )
    resolved = resolve_database_url(raw)
    u = make_url(resolved)
    assert u.username == "postgres"
    assert u.host == "db.ref.supabase.co"
    assert make_url(resolved).password == "p@ss:word"
    assert password_needs_url_encoding("p@ss:word")


def test_str_url_object_masks_password_but_render_does_not() -> None:
    from sqlalchemy.engine.url import URL

    built = URL.create(
        drivername="postgresql+asyncpg",
        username="postgres",
        password="real-secret",
        host="db.ref.supabase.co",
        port=5432,
        database="postgres",
    )
    assert make_url(str(built)).password == "***"
    assert make_url(built.render_as_string(hide_password=False)).password == "real-secret"


def test_resolve_database_url_does_not_mask_password() -> None:
    raw = (
        "postgresql+asyncpg://postgres:secretpass@db.ref.supabase.co:5432/"
        "postgres?ssl=require"
    )
    resolved = resolve_database_url(raw)
    assert make_url(resolved).password == "secretpass"


def test_database_password_override() -> None:
    raw = (
        "postgresql+asyncpg://postgres:wrong@db.ref.supabase.co:5432/"
        "postgres?ssl=require"
    )
    with patch("app.core.asyncpg_connect.settings") as s:
        s.database_url = raw
        s.database_password = "correct"
        resolved = resolve_database_url()
        assert make_url(resolved).password == "correct"  # noqa: S105
