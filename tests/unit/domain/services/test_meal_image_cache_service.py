import pytest
from unittest.mock import AsyncMock

from src.domain.model.meal_image_cache import CachedImage
from src.domain.services.meal_image_cache.meal_image_cache_service import (
    MealImageCacheService,
)
from tests.fakes.fake_embedding_adapter import FakeEmbeddingAdapter


@pytest.mark.asyncio
async def test_lookup_returns_hit_when_cosine_above_threshold():
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock(
        return_value=[
            CachedImage(
                meal_name="Grilled Salmon",
                name_slug="grilled-salmon",
                image_url="https://cdn/a.jpg",
                thumbnail_url=None,
                source="pexels",
                confidence=0.9,
                cosine=0.97,
            ),
        ]
    )
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)

    results = await svc.lookup_batch(["Grilled Lemon Salmon"])

    assert results[0] is not None
    assert results[0].image_url == "https://cdn/a.jpg"


@pytest.mark.asyncio
async def test_lookup_returns_none_when_below_threshold():
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock(
        return_value=[
            CachedImage(
                meal_name="Pizza",
                name_slug="pizza",
                image_url="https://cdn/b.jpg",
                thumbnail_url=None,
                source="pexels",
                confidence=0.8,
                cosine=0.80,
            ),
        ]
    )
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)
    assert await svc.lookup_batch(["Salad"]) == [None]


@pytest.mark.asyncio
async def test_lookup_returns_none_on_empty_index():
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock(return_value=[None])
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)
    assert await svc.lookup_batch(["Any"]) == [None]


@pytest.mark.asyncio
async def test_lookup_preserves_order_and_length():
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock(return_value=[None, None, None])
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)
    results = await svc.lookup_batch(["A", "B", "C"])
    assert len(results) == 3 and all(r is None for r in results)


@pytest.mark.asyncio
async def test_lookup_empty_input_returns_empty():
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock()
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)
    assert await svc.lookup_batch([]) == []
    cache.query_nearest_batch.assert_not_called()


@pytest.mark.asyncio
async def test_lookup_batch_uses_single_batch_query():
    """Verify batch lookup makes one query_nearest_batch call, not N query_nearest calls."""
    cache = AsyncMock()
    cache.query_nearest_batch = AsyncMock(
        return_value=[
            CachedImage(
                meal_name="Salmon",
                name_slug="salmon",
                image_url="https://cdn/a.jpg",
                thumbnail_url=None,
                source="pexels",
                confidence=0.9,
                cosine=0.97,
            ),
            CachedImage(
                meal_name="Salad",
                name_slug="salad",
                image_url="https://cdn/b.jpg",
                thumbnail_url=None,
                source="pexels",
                confidence=0.85,
                cosine=0.96,
            ),
        ]
    )
    svc = MealImageCacheService(cache, FakeEmbeddingAdapter(), dedup_threshold=0.95)

    results = await svc.lookup_batch(["Grilled Salmon", "Caesar Salad"])

    cache.query_nearest_batch.assert_called_once()
    assert len(results) == 2
    assert results[0].image_url == "https://cdn/a.jpg"
    assert results[1].image_url == "https://cdn/b.jpg"
