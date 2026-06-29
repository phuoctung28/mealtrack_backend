from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from src.api.routes.v1.meals import get_meal_value_insights
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

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ttl):
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


def _nutrition_with_repeated_chicken():
    return Nutrition(
        macros=Macros(protein=120, carbs=43, fat=15),
        food_items=[
            FoodItem(
                id="chicken-1",
                name="Chicken",
                quantity=150,
                unit="g",
                macros=Macros(protein=40, carbs=0, fat=5),
            ),
            FoodItem(
                id="chicken-2",
                name="Chicken",
                quantity=150,
                unit="g",
                macros=Macros(protein=40, carbs=0, fat=5),
            ),
            FoodItem(
                id="chicken-3",
                name="Chicken",
                quantity=150,
                unit="g",
                macros=Macros(protein=40, carbs=0, fat=5),
            ),
            FoodItem(
                id="rice-1",
                name="Rice",
                quantity=150,
                unit="g",
                macros=Macros(protein=4, carbs=43, fat=0.4),
            ),
        ],
    )


class FakeEventBus:
    def __init__(self, meal):
        self.meal = meal

    async def send(self, query):
        return self.meal


def _request(language: str = "en") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"accept-language", language.encode("utf-8"))],
        }
    )


@pytest.mark.asyncio
async def test_non_english_reuses_canonical_ai_result_and_caches_translation():
    ai_manager = AsyncMock()
    ai_manager.generate.return_value = {
        "meal_bullets": [
            {
                "text": "Egg adds protein for fullness and fat for satiety.",
                "category": "benefit",
                "highlights": ["fullness"],
            }
        ],
        "ingredient_insights": [
            {
                "ingredient_name": "Egg",
                "text": "Egg offers protein for recovery and fat for satisfaction.",
                "category": "balance",
                "highlights": ["recovery"],
            }
        ],
    }
    text_service = AsyncMock()
    text_service.translate_texts.return_value = [
        "Trứng bổ sung protein giúp no và chất béo giúp hài lòng.",
        "no",
        "Trứng",
        "Trứng cung cấp protein để phục hồi và chất béo để no lâu.",
        "phục hồi",
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
    assert (
        result.meal_bullets[0].text
        == "Trứng bổ sung protein giúp no và chất béo giúp hài lòng."
    )
    assert result.meal_bullets[0].highlights == ["no"]
    assert result.ingredient_insights[0].ingredient_name == "Trứng"
    assert result.ingredient_insights[0].highlights == ["phục hồi"]
    ai_manager.generate.assert_awaited_once()
    text_service.translate_texts.assert_awaited_once()
    assert len(cache.values) == 2


def test_version_matches_current_cache_key_for_english():
    service = MealValueInsightService()
    version = service.version(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="en",
    )
    expected = service._cache_key(
        service._summary(
            dish_name="Egg bowl",
            nutrition=_nutrition(),
            ingredient_names_by_id={},
            language="en",
            user_context={},
        )
    )

    assert version == expected


def test_summary_groups_repeated_ingredients_for_overview():
    summary = MealValueInsightService()._summary(
        dish_name="Chicken rice",
        nutrition=_nutrition_with_repeated_chicken(),
        ingredient_names_by_id={},
        language="en",
        user_context={},
    )

    chicken = summary["ingredient_overview"][0]
    assert chicken["name"] == "Chicken"
    assert chicken["count"] == 3
    assert chicken["total_quantity"] == 450
    assert chicken["repeated"] is True
    assert chicken["large_portion"] is True
    assert chicken["dominant_macro"] == "protein"
    assert "very_high_protein" in summary["risk_flags"]
    assert "repeated_protein_ingredient" in summary["risk_flags"]
    assert "large_protein_portion" in summary["risk_flags"]


@pytest.mark.asyncio
async def test_value_insights_endpoint_returns_fresh_cached_payload():
    meal = SimpleNamespace(
        meal_id="meal-1",
        dish_name="Egg bowl",
        nutrition=_nutrition(),
    )
    insights = MealValueInsights(
        meal_bullets=[
            ValueInsight(
                text="Egg adds protein for fullness and fat for satiety.",
                category="benefit",
                highlights=["fullness"],
            )
        ],
        ingredient_insights=[],
    )
    service = MealValueInsightService()
    cache_key = service.version(
        dish_name=meal.dish_name,
        nutrition=meal.nutrition,
        language="en",
    )
    cache = FakeCache()
    cache.values[cache_key] = serialize_insights(insights)

    response = await get_meal_value_insights(
        request=_request(),
        meal_id=meal.meal_id,
        user_id="user-1",
        event_bus=FakeEventBus(meal),
        cache_service=cache,
        task_manager=AsyncMock(),
        text_translation_service=None,
    )

    assert response.status == "fresh"
    assert response.version == cache_key
    assert response.value_insights is not None
    assert response.value_insights.meal_bullets[0].text == (
        "Egg adds protein for fullness and fat for satiety."
    )
    assert response.value_insights.meal_bullets[0].highlights == ["fullness"]


@pytest.mark.asyncio
async def test_localized_cache_hit_skips_ai_and_deepl():
    cached = MealValueInsights(
        meal_bullets=[
            ValueInsight(
                text="Trứng bổ sung protein giúp no và chất béo giúp hài lòng.",
                category="benefit",
                highlights=["no"],
            )
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
    assert (
        result.meal_bullets[0].text
        == "Trứng bổ sung protein giúp no và chất béo giúp hài lòng."
    )
    ai_manager.generate.assert_not_called()
    text_service.translate_texts.assert_not_called()


@pytest.mark.asyncio
async def test_cached_only_miss_skips_ai_generation():
    ai_manager = AsyncMock()
    cache = FakeCache()

    result = await MealValueInsightService(ai_manager=ai_manager).get_cached_ai(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="en",
        cache_service=cache,
    )

    assert result is None
    ai_manager.generate.assert_not_called()


@pytest.mark.asyncio
async def test_cached_only_hit_returns_cached_result():
    cached = MealValueInsights(
        meal_bullets=[
            ValueInsight(
                text="Egg adds protein for fullness and fat for satiety.",
                category="benefit",
                highlights=["fullness"],
            )
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
    cache.values[canonical_key] = serialize_insights(cached)
    ai_manager = AsyncMock()

    result = await MealValueInsightService(ai_manager=ai_manager).get_cached_ai(
        dish_name="Egg bowl",
        nutrition=_nutrition(),
        language="en",
        cache_service=cache,
    )

    assert result is not None
    assert result.meal_bullets[0].text == (
        "Egg adds protein for fullness and fat for satiety."
    )
    ai_manager.generate.assert_not_called()


@pytest.mark.asyncio
async def test_deepl_english_fallback_is_not_cached_as_localized_result():
    ai_manager = AsyncMock()
    ai_manager.generate.return_value = {
        "meal_bullets": [
            {
                "text": "Egg adds protein for fullness and fat for satiety.",
                "category": "benefit",
                "highlights": ["fullness"],
            }
        ],
        "ingredient_insights": [],
    }
    text_service = AsyncMock()
    text_service.translate_texts.return_value = [
        "Egg adds protein for fullness and fat for satiety.",
        "fullness",
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
    assert result.meal_bullets[0].text == (
        "Egg adds protein for fullness and fat for satiety."
    )
    assert len(cache.values) == 1
