import pytest
from unittest.mock import AsyncMock, MagicMock
import json

from src.domain.services.meal_suggestion.nutrition_lookup_service import (
    NutritionLookupService,
    IngredientMacros,
)


@pytest.mark.asyncio
async def test_lookup_checks_redis_before_db():
    """Verify Redis is checked before DB lookup."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=json.dumps({
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6,
        "fiber": 0.0,
        "sugar": 0.0,
        "source_tier": "T1_food_reference",
    }))

    repo_mock = MagicMock()
    repo_mock.find_by_normalized_name = MagicMock()  # Should NOT be called

    svc = NutritionLookupService(
        food_ref_repo=repo_mock,
        ingredient_nutrition_resolver=MagicMock(),
        generation_service=MagicMock(),
        redis_client=redis_mock,
    )

    result = await svc._lookup_ingredient("chicken breast", 150.0)

    redis_mock.get.assert_called_once()
    repo_mock.find_by_normalized_name.assert_not_called()
    assert result.protein == pytest.approx(46.5, rel=0.01)  # 31 * 1.5


@pytest.mark.asyncio
async def test_lookup_caches_result_in_redis_on_miss():
    """Verify successful lookup is cached in Redis."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)  # Cache miss
    redis_mock.setex = AsyncMock()

    repo_mock = MagicMock()
    repo_mock.find_by_normalized_name = MagicMock(return_value={
        "id": 1,
        "protein_100g": 31.0,
        "carbs_100g": 0.0,
        "fat_100g": 3.6,
        "fiber_100g": 0.0,
        "sugar_100g": 0.0,
    })

    svc = NutritionLookupService(
        food_ref_repo=repo_mock,
        ingredient_nutrition_resolver=MagicMock(),
        generation_service=MagicMock(),
        redis_client=redis_mock,
    )

    await svc._lookup_ingredient("chicken breast", 100.0)

    redis_mock.setex.assert_called_once()
    call_args = redis_mock.setex.call_args
    assert "nutrition:" in call_args[0][0]  # Key contains prefix
    assert call_args[0][1] == 86400  # TTL is 24 hours
