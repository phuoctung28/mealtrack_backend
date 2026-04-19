"""Async fixtures for repository integration tests.

Requires DATABASE_URL in environment (Neon Postgres).
Each test runs in an isolated transaction rolled back after.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def _make_async_pg_url() -> str:
    url = os.environ.get("DATABASE_URL_DIRECT") or os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping async integration tests")

    for old, new in [
        ("postgres://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
    ]:
        if url.startswith(old):
            url = url.replace(old, new, 1)
            break

    if "postgresql+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]

    return url


@pytest_asyncio.fixture()
async def async_pg_engine():
    """Function-scoped engine — avoids event-loop mismatch in asyncio_mode=strict."""
    engine = create_async_engine(_make_async_pg_url(), echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def async_db_session(async_pg_engine) -> AsyncSession:
    """Real Postgres async session — rolled back after each test."""
    async with async_pg_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()  # savepoint — absorbs session.commit() calls
        factory = async_sessionmaker(
            bind=conn,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        session = factory()
        try:
            yield session
        finally:
            await session.close()
            try:
                await conn.rollback()
            except Exception:
                pass
