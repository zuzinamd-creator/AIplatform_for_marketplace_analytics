from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.asyncpg_connect import asyncpg_connect_args, sqlalchemy_async_database_url

engine = create_async_engine(
    sqlalchemy_async_database_url(),
    pool_pre_ping=True,
    connect_args=asyncpg_connect_args(),
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        if db.in_transaction():
            await db.rollback()
        await db.close()
