"""PostgreSQL-backed degraded-mode checks for catalog search."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.handlers.query_handlers.search_foods_query_handler import (
    SearchFoodsQueryHandler,
)
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.services.food_mapping_service import FoodMappingService
from src.infra.repositories.food_reference_repository_async import (
    AsyncFoodReferenceRepository,
)

pytestmark = pytest.mark.integration


class _BrokenCache:
    async def get_cached_search(self, key: str):
        raise RuntimeError("redis unavailable")

    async def cache_search(self, key: str, value):
        raise RuntimeError("redis unavailable")


class _BrokenProvider:
    async def search_foods(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


@pytest.mark.asyncio
async def test_food_search_returns_local_results_when_cache_and_provider_are_down(
    pg_session: AsyncSession,
):
    food_repo = AsyncFoodReferenceRepository(pg_session)
    reference = await food_repo.upsert_by_normalized_name(
        name="Rice",
        name_normalized="rice",
        protein_100g=2.7,
        carbs_100g=28.0,
        fat_100g=0.3,
        fiber_100g=0.4,
        sugar_100g=0.1,
        source="catalog_seed",
        is_verified=True,
    )
    await pg_session.commit()
    assert reference is not None

    local_search = AsyncMock(side_effect=food_repo.search_local)
    handler = SearchFoodsQueryHandler(
        cache_service=_BrokenCache(),
        mapping_service=FoodMappingService(),
        fat_secret_service=_BrokenProvider(),
        local_search=local_search,
    )

    result = await handler.handle(SearchFoodsQuery(query="rice", language="en", limit=5))

    local_search.assert_awaited_once_with("rice", "US", 5)
    assert result["total"] == 1
    assert result["results"][0]["source"] == "food_reference"
    assert result["results"][0]["food_reference_id"] == reference["id"]
