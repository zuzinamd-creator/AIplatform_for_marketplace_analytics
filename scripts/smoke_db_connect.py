"""Smoke test: MAIN Supabase Postgres connectivity via asyncpg (+ SQLAlchemy check)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.asyncpg_connect import (
    asyncpg_connect_args,
    debug_database_url,
    resolve_database_url,
    sqlalchemy_async_database_url,
)
from app.core.config import reload_settings
from app.core.environment import detect_environment


def _print_debug() -> None:
    reload_settings()
    d = debug_database_url()
    masked = make_url(sqlalchemy_async_database_url()).render_as_string(hide_password=True)
    print("--- DATABASE_URL debug ---")
    print(f"env DATABASE_URL set: {d.env_database_url_present}")
    if d.env_database_url_present:
        print(f"  env parsed username: {d.env_database_url_username}")
        if d.env_database_url_username != d.settings_database_url_username:
            print(
                "  WARNING: OS env DATABASE_URL overrides .env "
                f"(settings username={d.settings_database_url_username})"
            )
    print(f"settings .env username: {d.settings_database_url_username}")
    print(f"resolved username:     {d.resolved_username}")
    print(f"hostname:              {d.hostname}")
    print(f"database:              {d.database}")
    print(f"port:                  {d.port}")
    print(f"ssl required:          {d.ssl_required}")
    print(f"password length:       {d.password_length}")
    print(f"password needs encode: {d.password_needs_encoding}")
    print(f"DATABASE_PASSWORD override: {d.database_password_override}")
    print(f"asyncpg connect user:  {d.asyncpg_connect_user}")
    print(f"direct supabase host:  {d.direct_supabase_host}")
    print(f"note: {d.note}")
    print(f"engine URL (masked):   {masked}")
    print("--------------------------")


async def _smoke_asyncpg() -> tuple[int, str, str]:
    u = make_url(resolve_database_url())
    connect_kwargs = {
        "user": u.username,
        "password": u.password,
        "host": u.host,
        "port": u.port or 5432,
        "database": u.database,
        "timeout": 60,
        "command_timeout": 60,
        **asyncpg_connect_args(),
    }
    last_exc: Exception | None = None
    for attempt in range(3):
        conn = None
        try:
            conn = await asyncpg.connect(**connect_kwargs)
            one = await conn.fetchval("SELECT 1")
            db_name = await conn.fetchval("SELECT current_database()")
            session_user = await conn.fetchval("SELECT current_user")
            return int(one), str(db_name), str(session_user)
        except (asyncpg.exceptions.ConnectionDoesNotExistError, OSError) as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(1.5)
                continue
            raise
        finally:
            if conn is not None:
                try:
                    await conn.close()
                except OSError:
                    pass
    raise last_exc or RuntimeError("smoke_asyncpg failed")


async def _smoke_sqlalchemy() -> None:
    engine = create_async_engine(
        sqlalchemy_async_database_url(),
        pool_pre_ping=True,
        connect_args=asyncpg_connect_args(),
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def main() -> int:
    _print_debug()

    env = detect_environment()
    print(f"environment_mode={env.mode} db_host={env.db_host} ephemeral={env.is_ephemeral}")

    ssl_ctx = asyncpg_connect_args().get("ssl")
    print(f"ssl_enabled={ssl_ctx is not None} ssl_verify_mode={getattr(ssl_ctx, 'verify_mode', None)}")

    try:
        one, db_name, session_user = await _smoke_asyncpg()
        print(f"ok asyncpg SELECT 1 => {one} database={db_name} current_user={session_user}")
        try:
            await _smoke_sqlalchemy()
            print("ok SQLAlchemy engine.connect() + SELECT 1")
        except Exception as sa_exc:
            print(f"SQLAlchemy check skipped/failed (asyncpg ok): {type(sa_exc).__name__}: {sa_exc}")
        return 0
    except Exception as exc:
        print(f"connection failed: {type(exc).__name__}: {exc}")
        print(
            "If asyncpg_connect_user is postgres.<ref> but error says user \"postgres\", "
            "that is often Supabase wording - verify password in Dashboard / Database."
        )
        print("For passwords with @ : / # use DATABASE_PASSWORD in .env or URL-encode the password.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
