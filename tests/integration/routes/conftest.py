"""
Route-level conftest: provides a SQLite-backed test_session so route tests
run without a real database connection. All route tests mock the event bus
and don't issue any DB queries; this fixture only satisfies the fixture
dependency declared in each test module's `client` fixture.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infra.database.config import Base
from src.infra.database import models  # noqa: F401 – registers ORM metadata


@pytest.fixture(scope="function")
def test_session() -> Session:
    """In-memory SQLite session — no network required."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
