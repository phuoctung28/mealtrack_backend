from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from src.domain.model.meal_image_cache import CachedImageUpsert
from src.infra.repositories.pgvector_meal_image_cache_repository_async import (
    AsyncPgvectorMealImageCacheRepository,
)


class _Rows:
    def fetchall(self):
        return []


class _AsyncCapturingSession:
    def __init__(self, exc: Exception | None = None):
        self.exc = exc
        self.statement = None
        self.params = None
        self.rollback = AsyncMock()
        self.flush = AsyncMock()

    async def execute(self, statement, params=None):
        self.statement = statement
        self.params = params
        if self.exc:
            raise self.exc
        return _Rows()


@pytest.mark.asyncio
async def test_query_nearest_batch_binds_embedding_array_before_cast():
    session = _AsyncCapturingSession()
    repo = AsyncPgvectorMealImageCacheRepository(session)

    await repo.query_nearest_batch([[0.0] * 768])

    bind_names = set(session.statement._bindparams.keys())
    assert "emb_array" in bind_names
    dialect = postgresql.psycopg2.dialect()
    compiled = str(session.statement.compile(dialect=dialect))
    assert "UNNEST(%(emb_array)s::TEXT[])" in compiled
    assert session.params == {"emb_array": [str([0.0] * 768)]}


@pytest.mark.asyncio
async def test_query_nearest_batch_rolls_back_failed_session():
    session = _AsyncCapturingSession(exc=RuntimeError("db failed"))
    repo = AsyncPgvectorMealImageCacheRepository(session)

    with pytest.raises(RuntimeError, match="db failed"):
        await repo.query_nearest_batch([[0.0] * 768])

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_flushes_without_committing():
    session = _AsyncCapturingSession()
    repo = AsyncPgvectorMealImageCacheRepository(session)

    await repo.upsert(
        CachedImageUpsert(
            meal_name="Rice Bowl",
            name_slug="rice-bowl",
            text_embedding=[0.1] * 768,
            image_url="https://example.com/rice.jpg",
            thumbnail_url=None,
            source="test",
            confidence=0.9,
        )
    )

    session.flush.assert_awaited_once()
    assert not hasattr(session, "commit")
