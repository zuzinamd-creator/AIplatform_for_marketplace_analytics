from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

_ALEMBIC_DIR = Path(__file__).resolve().parent
if str(_ALEMBIC_DIR) not in sys.path:
    sys.path.insert(0, str(_ALEMBIC_DIR))

import app.models  # noqa: F401
from alembic import context
from app.core.asyncpg_connect import asyncpg_connect_args, sqlalchemy_async_database_url
from app.core.config import settings
from app.models import Base
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_migration_url = (settings.alembic_database_url or settings.database_url).strip()
config.set_main_option(
    "sqlalchemy.url",
    sqlalchemy_async_database_url(_migration_url) if _migration_url else settings.async_database_url,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    if settings.alembic_bypass_rls:
        connection.execute(text("SELECT set_config('app.bypass_rls', 'true', false)"))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    migration_url = (settings.alembic_database_url or settings.database_url).strip()
    connectable = create_async_engine(
        sqlalchemy_async_database_url(migration_url),
        poolclass=pool.NullPool,
        connect_args=asyncpg_connect_args(migration_url),
    )

    # begin() commits on success; connect() alone leaves DDL uncommitted with asyncpg.
    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
