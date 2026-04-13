"""Unit tests for FoodImageSearchService — caching, validation, and adapter chain."""
from unittest.mock import AsyncMock

import pytest

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.services.meal_discovery.food_image_search_service import (
    FoodImageSearchService,
)


def _make_result(alt: str = "grilled chicken on plate") -> FoodImageResult:
    return FoodImageResult(
        url="https://cdn.example/a.jpg",
        thumbnail_url="https://cdn.example/a_thumb.jpg",
        source="pexels",
        photographer="Jane Doe",
        alt_text=alt,
    )


@pytest.mark.asyncio
class TestFoodImageSearchService:
    async def test_returns_first_adapter_hit_and_caches(self):
        expected = _make_result()
        adapter_a = AsyncMock()
        adapter_a.search = AsyncMock(return_value=expected)
        adapter_b = AsyncMock()
        adapter_b.search = AsyncMock(return_value=None)

        service = FoodImageSearchService(adapters=[adapter_a, adapter_b])

        first = await service.search_food_image("Grilled Chicken")
        assert first is expected
        # Second call for same normalized key must hit cache — no new adapter call
        second = await service.search_food_image("  grilled chicken  ")
        assert second is expected
        assert adapter_a.search.call_count == 1
        # Secondary adapter was never tried because primary hit
        adapter_b.search.assert_not_awaited()

    async def test_falls_back_to_second_adapter(self):
        expected = _make_result(alt="salmon fillet grilled")
        adapter_a = AsyncMock()
        adapter_a.search = AsyncMock(return_value=None)
        adapter_b = AsyncMock()
        adapter_b.search = AsyncMock(return_value=expected)

        service = FoodImageSearchService(adapters=[adapter_a, adapter_b])
        result = await service.search_food_image("grilled salmon")

        assert result is expected
        adapter_a.search.assert_awaited_once()
        adapter_b.search.assert_awaited_once()

    async def test_returns_none_when_all_adapters_miss(self):
        adapter = AsyncMock()
        adapter.search = AsyncMock(return_value=None)

        service = FoodImageSearchService(adapters=[adapter])
        result = await service.search_food_image("obscure dish xyzzy")

        assert result is None

    async def test_rejects_image_with_irrelevant_alt_text(self):
        # alt text with no food/query overlap is rejected
        bad = FoodImageResult(
            url="https://x/a.jpg",
            thumbnail_url="https://x/a_t.jpg",
            source="pexels",
            alt_text="skyscraper city building",
        )
        adapter = AsyncMock()
        adapter.search = AsyncMock(return_value=bad)

        service = FoodImageSearchService(adapters=[adapter])
        result = await service.search_food_image("grilled chicken")

        # Rejected; after simplified fallback still no match → None
        assert result is None

    async def test_accepts_image_when_alt_matches_food_signal(self):
        good = FoodImageResult(
            url="https://x/b.jpg",
            thumbnail_url="https://x/b_t.jpg",
            source="unsplash",
            alt_text="sauce drizzled over rice",  # 'rice' is a food signal
        )
        adapter = AsyncMock()
        adapter.search = AsyncMock(return_value=good)

        service = FoodImageSearchService(adapters=[adapter])
        result = await service.search_food_image("exotic pilaf")
        assert result is good

    async def test_accepts_image_with_empty_alt_text(self):
        empty_alt = FoodImageResult(
            url="https://x/c.jpg",
            thumbnail_url="https://x/c_t.jpg",
            source="pexels",
            alt_text="",
        )
        adapter = AsyncMock()
        adapter.search = AsyncMock(return_value=empty_alt)

        service = FoodImageSearchService(adapters=[adapter])
        result = await service.search_food_image("anything")
        assert result is empty_alt

    async def test_swallows_adapter_exception_and_continues(self):
        raising = AsyncMock()
        raising.search = AsyncMock(side_effect=RuntimeError("boom"))
        raising.__class__ = type("Raiser", (), {})
        fallback = AsyncMock()
        fallback.search = AsyncMock(return_value=_make_result())

        service = FoodImageSearchService(adapters=[raising, fallback])
        result = await service.search_food_image("grilled chicken")
        assert result is not None
