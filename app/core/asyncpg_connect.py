"""Shared asyncpg connect_args (SSL for Supabase direct / managed Postgres)."""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qs, quote, urlparse

import certifi
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.engine import make_url
from sqlalchemy.engine.url import URL

from app.core.config import settings

_PASSWORD_UNSAFE = frozenset("@:/\\?#[]&=%+")


def password_needs_url_encoding(password: str | None) -> bool:
    if not password:
        return False
    return any(ch in _PASSWORD_UNSAFE for ch in password)


def _ensure_asyncpg_driver(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def resolve_database_url(raw_url: str | None = None) -> str:
    """
    Canonical DATABASE_URL: SQLAlchemy URL.create (safe password encoding).

    Optional DATABASE_PASSWORD env overrides password from URL (avoids broken parsing).
    """
    raw = _ensure_asyncpg_driver(raw_url or settings.database_url)
    parsed = make_url(raw)

    password = (settings.database_password or "").strip() or parsed.password
    username = parsed.username or ""
    host = parsed.host or ""
    port = parsed.port or 5432
    database = (parsed.database or "").lstrip("/") or "postgres"
    query = dict(parsed.query)

    built = URL.create(
        drivername="postgresql+asyncpg",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        query=query,
    )
    # str(url) masks password as "***"; asyncpg would get literal "***" on reconnect.
    return built.render_as_string(hide_password=False)


@dataclass(frozen=True)
class DatabaseUrlDebug:
    env_database_url_present: bool
    env_database_url_username: str | None
    settings_database_url_username: str | None
    resolved_username: str | None
    hostname: str | None
    database: str | None
    port: int | None
    ssl_required: bool
    password_length: int
    password_needs_encoding: bool
    database_password_override: bool
    asyncpg_connect_user: str | None
    direct_supabase_host: bool
    note: str


def debug_database_url(raw_url: str | None = None) -> DatabaseUrlDebug:
    import os

    from app.core.environment import is_supabase_direct_host

    env_raw = os.environ.get("DATABASE_URL")
    env_user: str | None = None
    if env_raw:
        try:
            env_user = make_url(_ensure_asyncpg_driver(env_raw)).username
        except Exception:
            env_user = "<parse-error>"

    settings_user: str | None = None
    try:
        settings_user = make_url(_ensure_asyncpg_driver(settings.database_url)).username
    except Exception:
        settings_user = "<parse-error>"

    raw = _ensure_asyncpg_driver(raw_url or settings.database_url)
    source = make_url(raw)
    resolved = resolve_database_url(raw_url)
    u = make_url(resolved)
    pwd = (settings.database_password or "").strip() or source.password or ""
    engine_url = sqlalchemy_async_database_url(resolved)
    _, asyncpg_opts = PGDialect_asyncpg().create_connect_args(make_url(engine_url))
    host = u.host or ""
    user = u.username or ""
    return DatabaseUrlDebug(
        env_database_url_present=bool(env_raw),
        env_database_url_username=env_user,
        settings_database_url_username=settings_user,
        resolved_username=user,
        hostname=host,
        database=(u.database or "").lstrip("/") or None,
        port=u.port,
        ssl_required=database_url_requires_ssl(resolved),
        password_length=len(pwd),
        password_needs_encoding=password_needs_url_encoding(pwd),
        database_password_override=bool((settings.database_password or "").strip()),
        asyncpg_connect_user=asyncpg_opts.get("user"),
        direct_supabase_host=is_supabase_direct_host(host),
        note="MAIN requires direct host db.<project-ref>.supabase.co with ?ssl=require.",
    )


@lru_cache(maxsize=1)
def build_verified_ssl_context() -> ssl.SSLContext:
    """Direct Supabase host (db.*.supabase.co): full CA verification via certifi."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    extra_ca = settings.database_ssl_extra_ca_file.strip()
    if extra_ca:
        ctx.load_verify_locations(cafile=extra_ca)
    return ctx


def database_url_requires_ssl(url: str) -> bool:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    qs = parse_qs(parsed.query)
    ssl_vals = qs.get("ssl", []) + qs.get("sslmode", [])
    for raw in ssl_vals:
        val = raw.lower()
        if val in ("require", "verify-ca", "verify-full", "true", "1"):
            return True
    return False


def sqlalchemy_async_database_url(database_url: str | None = None) -> str:
    """
    Engine URL without ssl/sslmode query keys — TLS is configured via connect_args only.
    """
    url = resolve_database_url(database_url)
    u = make_url(url)
    query = {k: v for k, v in u.query.items() if k not in ("ssl", "sslmode")}
    return u.set(query=query).render_as_string(hide_password=False)


def asyncpg_connect_args(database_url: str | None = None) -> dict:
    url = resolve_database_url(database_url)
    connect_args: dict = {}

    if database_url_requires_ssl(url):
        connect_args["ssl"] = build_verified_ssl_context()

    return connect_args


def format_database_url_for_env(
    *,
    project_ref: str,
    password: str,
    region: str = "eu-west-1",
) -> str:
    """Build a validated direct Supabase URL (password URL-encoded when needed)."""
    del region  # kept for callers that still pass region from Dashboard copy-paste
    user = "postgres"
    host = f"db.{project_ref}.supabase.co"
    safe_password = quote(password, safe="")
    return (
        f"postgresql+asyncpg://{user}:{safe_password}@{host}:5432/postgres?ssl=require"
    )
