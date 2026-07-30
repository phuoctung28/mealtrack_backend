from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.app.queries.user import GetUserProfileQuery
from src.app.services.meal_value_insight_scheduler import (
    build_value_insights_for_meal_with_profile,
    compact_meal_insight_user_context,
    schedule_value_insight_generation,
)
from src.domain.model.nutrition import Macros, Nutrition


class FakeTaskManager:
    def __init__(self):
        self.spawned = []

    def spawn(self, name, coroutine):
        self.spawned.append((name, coroutine))


class FakeCache:
    async def get(self, key):
        return None

    async def set(self, key, value, ttl):
        return True


class FakeEventBus:
    def __init__(self, profile_result):
        self.profile_result = profile_result
        self.queries = []

    async def send(self, query):
        self.queries.append(query)
        if isinstance(query, GetUserProfileQuery):
            return self.profile_result
        raise AssertionError(f"Unexpected query: {query!r}")


def _meal():
    return SimpleNamespace(
        meal_id="meal-1",
        dish_name="Chicken rice",
        nutrition=Nutrition(macros=Macros(protein=40, carbs=55, fat=12)),
    )


def _profile_result():
    return {
        "profile": {
            "fitness_goal": "lose_weight",
            "dietary_preferences": ["high_protein"],
            "health_conditions": ["hypertension"],
            "allergies": ["peanut"],
            "meals_per_day": 3,
            "snacks_per_day": 1,
            "training_level": "intermediate",
            "custom_protein_g": 140,
            "custom_carbs_g": 180,
            "custom_fat_g": 60,
        },
        "tdee": {
            "tdee": 2300,
            "target_calories": 1900,
            "protein_g": 140,
            "carbs_g": 180,
            "fat_g": 60,
        },
    }


def test_compact_meal_insight_user_context_keeps_safe_profile_fields():
    context = compact_meal_insight_user_context(_profile_result())

    assert context == {
        "fitness_goal": "lose_weight",
        "dietary_preferences": ["high_protein"],
        "health_conditions": ["hypertension"],
        "allergies": ["peanut"],
        "meals_per_day": 3,
        "snacks_per_day": 1,
        "training_level": "intermediate",
        "custom_macros": {
            "custom_protein_g": 140,
            "custom_carbs_g": 180,
            "custom_fat_g": 60,
        },
        "targets": {
            "tdee": 2300,
            "target_calories": 1900,
            "protein_g": 140,
            "carbs_g": 180,
            "fat_g": 60,
        },
    }


def test_schedule_value_insight_generation_spawns_profile_aware_task():
    task_manager = FakeTaskManager()

    scheduled = schedule_value_insight_generation(
        task_manager,
        _meal(),
        language="en",
        cache_service=FakeCache(),
        ai_manager=AsyncMock(),
        event_bus=FakeEventBus(_profile_result()),
        user_id="user-1",
        source="meal_analyze_graph",
    )

    assert scheduled is True
    assert task_manager.spawned
    name, coroutine = task_manager.spawned[0]
    assert name == "meal-value-insights:meal-1"
    coroutine.close()


def test_schedule_value_insight_generation_returns_false_without_prerequisites():
    scheduled = schedule_value_insight_generation(
        None,
        _meal(),
        language="en",
        cache_service=FakeCache(),
        ai_manager=AsyncMock(),
        event_bus=FakeEventBus(_profile_result()),
        user_id="user-1",
        source="meal_analyze_graph",
    )

    assert scheduled is False


@pytest.mark.asyncio
async def test_build_value_insights_for_meal_with_profile_includes_user_context():
    ai_manager = AsyncMock()
    ai_manager.generate.return_value = {
        "meal_bullets": [
            {
                "text": "Protein supports fullness for this goal.",
                "category": "benefit",
                "highlights": ["fullness"],
            }
        ],
        "ingredient_insights": [],
    }
    event_bus = FakeEventBus(_profile_result())

    await build_value_insights_for_meal_with_profile(
        _meal(),
        language="en",
        cache_service=FakeCache(),
        ai_manager=ai_manager,
        event_bus=event_bus,
        user_id="user-1",
    )

    prompt = ai_manager.generate.await_args.kwargs["prompt"]
    assert '"fitness_goal": "lose_weight"' in prompt
    assert '"allergies": ["peanut"]' in prompt
    assert '"target_calories": 1900' in prompt
