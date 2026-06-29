from unittest.mock import AsyncMock

import pytest

from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.services.meal_value_insight_contract import (
    MealValueInsights,
    ValueInsight,
    serialize_insights,
)
from src.domain.services.meal_value_insight_service import MealValueInsightService


class FakeCache:
    def __init__(self):
        self.values = {}

    async def get_json(self, key):
        return self.values.get(key)

    async def set_json(self, key, value, ttl):
        self.values[key] = value
        return True


def _nutrition():
    return Nutrition(
        macros=Macros(protein=20, carbs=30, fat=10),
        food_items=[
            FoodItem(
                id="egg-1",
                name="Egg",
                quantity=100,
                unit="g",
                macros=Macros(protein=12, carbs=1, fat=10),
            )
        ],
    )


@pytest.mark.asyncio
async def test_non_english_reuses_canonical_ai_result_and_caches_translation():
    ai_manager = AsyncMock()
    ai_manager.generate.return_value = {
        "meal_bullets": [
            {"text": "Egg adds protein and fat for satiety.", "category": "benefit"}
        ],
        "ingredient_insights": [
            {
                "ingredient_name": "Egg",
                "text": "A compact source of protein and fat.",
                "category": "balance",
            }
        ],
    }
    text_service = AsyncMock()
    text_service.translate_texts.return_value = [
        "Trứng bổ sung protein và chất béo giúp no lâu.",
        "Trứng",
        "Nguồn protein và chất béo nhỏ gọn.",
    ]
    cache = FakeCache()
    service = MealValueInsightService(
        ai_manager=ai_manager,
        text_translation_service=text_service,
    )

    result = await service.build_ai(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="vi",
        cache_service=cache,
    )

    assert result is not None
    assert result.meal_bullets[0].text == "Trứng bổ sung protein và chất béo giúp no lâu."
    assert result.ingredient_insights[0].ingredient_name == "Trứng"
    ai_manager.generate.assert_awaited_once()
    text_service.translate_texts.assert_awaited_once()
    assert len(cache.values) == 2


@pytest.mark.asyncio
async def test_localized_cache_hit_skips_ai_and_deepl():
    cached = MealValueInsights(
        meal_bullets=[
            ValueInsight(text="Trứng bổ sung protein.", category="benefit")
        ],
        ingredient_insights=[],
    )
    canonical_key = MealValueInsightService()._cache_key(
        MealValueInsightService()._summary(
            dish_name="Egg bowl",
            nutrition=_nutrition(),
            ingredient_names_by_id={},
            language="en",
            user_context={},
        )
    )
    cache = FakeCache()
    cache.values[f"{canonical_key}:lang:vi"] = serialize_insights(cached)
    ai_manager = AsyncMock()
    text_service = AsyncMock()

    result = await MealValueInsightService(
        ai_manager=ai_manager,
        text_translation_service=text_service,
    ).build_ai(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="vi",
        cache_service=cache,
    )

    assert result is not None
    assert result.meal_bullets[0].text == "Trứng bổ sung protein."
    ai_manager.generate.assert_not_called()
    text_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_deepl_english_fallback_is_not_cached_as_localized_result():
    ai_manager = AsyncMock()
    ai_manager.generate.return_value = {
        "meal_bullets": [
            {"text": "Egg adds protein and fat for satiety.", "category": "benefit"}
        ],
        "ingredient_insights": [],
    }
    text_service = AsyncMock()
    text_service.translate_texts.return_value = [
        "Egg adds protein and fat for satiety.",
    ]
    cache = FakeCache()

    result = await MealValueInsightService(
        ai_manager=ai_manager,
        text_translation_service=text_service,
    ).build_ai(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="vi",
        cache_service=cache,
    )

    assert result is not None
    assert result.meal_bullets[0].text == "Egg adds protein and fat for satiety."
    assert len(cache.values) == 1
