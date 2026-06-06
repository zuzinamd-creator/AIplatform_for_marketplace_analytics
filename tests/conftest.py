import os
from collections.abc import AsyncGenerator

import pytest
from app.core.database import get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _default_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    # Local integration default (see .env DATABASE_URL on port 5434).
    return "postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test"


TEST_DATABASE_URL = _default_test_database_url()

# Production identities that must never be targeted by automated tests/scripts.
PROTECTED_PRODUCTION_EMAILS = frozenset({"margarita.zuzina@mail.ru"})
PROTECTED_PRODUCTION_USER_IDS = frozenset({"caefecb3-5789-4878-a9d4-929be573fbcc"})


def assert_not_production_identity(*, email: str | None = None, user_id: str | None = None) -> None:
    if email and email.lower() in PROTECTED_PRODUCTION_EMAILS:
        raise RuntimeError(f"Refusing to run against production account: {email}")
    if user_id and user_id in PROTECTED_PRODUCTION_USER_IDS:
        raise RuntimeError(f"Refusing to run against production user_id: {user_id}")


@pytest.fixture
def integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"


@pytest.fixture
async def db_engine(integration_enabled: bool):
    if not integration_enabled:
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests")
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with engine.connect() as conn:
        has_users = await conn.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'users'"
                ")"
            )
        )
        if not has_users.scalar():
            await engine.dispose()
            pytest.fail(
                "Integration DB schema is missing (no public.users). "
                f"Run: alembic upgrade head  (TEST_DATABASE_URL={TEST_DATABASE_URL})"
            )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Uses schema created by Alembic (see CI workflow)."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def api_client(integration_enabled: bool) -> AsyncGenerator[AsyncClient, None]:
    if not integration_enabled:
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests")

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
