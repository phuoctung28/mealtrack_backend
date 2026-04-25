import pytest

from src.domain.model.meal_image_cache import CachedImageUpsert
from src.infra.repositories.pgvector_meal_image_cache_repository import (
    PgvectorMealImageCacheRepository,
)


@pytest.fixture
def sample_embedding():
    v = [0.0] * 512
    v[0] = 1.0
    return v


@pytest.mark.asyncio
async def test_upsert_then_query_roundtrip(db_session, sample_embedding):
    repo = PgvectorMealImageCacheRepository(db_session)
    await repo.upsert(
        CachedImageUpsert(
            meal_name="Grilled Salmon",
            name_slug="grilled-salmon",
            text_embedding=sample_embedding,
            image_url="https://cdn/a.jpg",
            thumbnail_url=None,
            source="pexels",
            confidence=0.91,
        )
    )
    hit = await repo.query_nearest(sample_embedding)
    assert hit is not None
    assert hit.meal_name == "Grilled Salmon"
    assert hit.cosine == pytest.approx(1.0, abs=1e-4)


@pytest.mark.asyncio
async def test_query_empty_returns_none(db_session, sample_embedding):
    repo = PgvectorMealImageCacheRepository(db_session)
    assert await repo.query_nearest(sample_embedding) is None


@pytest.mark.asyncio
async def test_upsert_idempotent_by_slug(db_session, sample_embedding):
    repo = PgvectorMealImageCacheRepository(db_session)
    for url in ["https://cdn/1.jpg", "https://cdn/2.jpg"]:
        await repo.upsert(
            CachedImageUpsert(
                meal_name="Pizza",
                name_slug="pizza",
                text_embedding=sample_embedding,
                image_url=url,
                thumbnail_url=None,
                source="pexels",
                confidence=0.9,
            )
        )
    hit = await repo.query_nearest(sample_embedding)
    assert hit is not None
    assert hit.image_url == "https://cdn/2.jpg"
