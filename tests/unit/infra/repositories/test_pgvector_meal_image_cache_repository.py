import pytest
from sqlalchemy.dialects import postgresql

from src.infra.repositories.pgvector_meal_image_cache_repository import (
    PgvectorMealImageCacheRepository,
)


class _Rows:
    def fetchall(self):
        return []


class _CapturingSession:
    def __init__(self, exc: Exception | None = None):
        self.exc = exc
        self.statement = None
        self.params = None
        self.rollback_called = False

    def execute(self, statement, params=None):
        self.statement = statement
        self.params = params
        if self.exc:
            raise self.exc
        return _Rows()

    def rollback(self):
        self.rollback_called = True


@pytest.mark.asyncio
async def test_query_nearest_batch_binds_embedding_array_before_cast():
    session = _CapturingSession()
    repo = PgvectorMealImageCacheRepository(session)

    await repo.query_nearest_batch([[0.0] * 512])

    bind_names = set(session.statement._bindparams.keys())
    assert "emb_array" in bind_names
    assert "emb_arra" not in bind_names
    dialect = postgresql.psycopg2.dialect()
    compiled = str(session.statement.compile(dialect=dialect))
    assert "UNNEST(%(emb_array)s::TEXT[])" in compiled
    assert session.params == {"emb_array": [str([0.0] * 512)]}


@pytest.mark.asyncio
async def test_query_nearest_batch_rolls_back_failed_session():
    session = _CapturingSession(exc=RuntimeError("db failed"))
    repo = PgvectorMealImageCacheRepository(session)

    with pytest.raises(RuntimeError, match="db failed"):
        await repo.query_nearest_batch([[0.0] * 512])

    assert session.rollback_called is True
