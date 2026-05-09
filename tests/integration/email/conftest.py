"""Conftest for email integration tests.

These tests do not require a real database — override test_engine with SQLite
so the autouse mock_scoped_session fixture chain can resolve without a live DB.
"""

import pytest
from sqlalchemy import create_engine

from src.infra.database.config import Base


@pytest.fixture(scope="session")
def test_engine(worker_id):
    """SQLite in-memory engine for email integration tests (no DB required)."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, echo=False
    )
    from src.infra.database import models  # noqa: F401 — register all ORM models

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
