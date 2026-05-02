"""
Integration test configuration.

Overrides test_engine and test_session to use SQLite in-memory for tests
that do not require a real database, avoiding MySQL connection errors.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typing import Generator

from src.infra.database.config import Base


@pytest.fixture(scope="session")
def test_engine(worker_id, request):
    """Override: use SQLite in-memory for all integration tests here."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    from src.infra.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine) -> Generator[Session, None, None]:
    """Provide a test database session backed by SQLite in-memory."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = SessionLocal()
    session.connection = connection

    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            pass
