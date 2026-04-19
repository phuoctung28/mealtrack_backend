"""Fixtures for pgvector repository integration tests.

These tests require a real Postgres DB with the vector extension installed.
They connect directly using DATABASE_URL from the environment (Neon Postgres).
Each test runs in an isolated transaction that is rolled back after.

We override root conftest fixtures that assume MySQL to prevent interference.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


def _make_pg_engine():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping pgvector integration tests")

    # Normalise to psycopg2 driver
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Neon requires SSL — inject if not already present
    if "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"

    return create_engine(url, echo=False, pool_pre_ping=True)


@pytest.fixture(scope="module")
def pg_engine():
    engine = _make_pg_engine()
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(pg_engine) -> Session:
    """Real Postgres session — rolled back after each test."""
    connection = pg_engine.connect()
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    connection.commit()

    transaction = connection.begin()
    factory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        except Exception:
            pass
        connection.close()


# Override root conftest autouse fixtures so they don't try to create MySQL schemas
@pytest.fixture(autouse=True)
def mock_scoped_session(db_session):
    """No-op override — pgvector tests manage their own session."""
    yield


@pytest.fixture(scope="session")
def test_engine(pg_engine):
    """Override root test_engine to use Postgres instead of MySQL."""
    return pg_engine


@pytest.fixture()
def test_session(db_session):
    """Override root test_session to use our real Postgres session."""
    return db_session
