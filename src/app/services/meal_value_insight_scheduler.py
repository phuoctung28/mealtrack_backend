"""Profile-aware scheduling helpers for meal value insights."""

import logging
from collections.abc import Coroutine
from typing import Any, Protocol

from src.app.queries.user import GetUserProfileQuery
from src.domain.ports.cache_port import CachePort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort
from src.domain.services.meal_value_insight_service import MealValueInsightService

logger = logging.getLogger(__name__)


class MealInsightEventBus(Protocol):
    """Event bus behavior needed to fetch user profile context."""

    async def send(self, event: Any) -> Any: ...


class MealInsightTaskScheduler(Protocol):
    """Background task behavior needed to schedule insight generation."""

    def spawn(
        self,
        name: str,
        coro: Coroutine[Any, Any, Any],
    ) -> Any: ...


def compact_meal_insight_user_context(
    profile_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the safe, stable profile subset used to personalize meal insights."""
    if not profile_result or not isinstance(profile_result, dict):
        return {}

    profile = profile_result.get("profile") or {}
    tdee = profile_result.get("tdee") or {}
    context: dict[str, Any] = {}

    for key in (
        "fitness_goal",
        "dietary_preferences",
        "health_conditions",
        "allergies",
        "meals_per_day",
        "snacks_per_day",
        "training_level",
    ):
        value = profile.get(key)
        if value not in (None, "", []):
            context[key] = value

    custom_macros = {
        key: profile.get(key)
        for key in ("custom_protein_g", "custom_carbs_g", "custom_fat_g")
        if profile.get(key) is not None
    }
    if custom_macros:
        context["custom_macros"] = custom_macros

    tdee_context = {
        key: tdee.get(key)
        for key in (
            "tdee",
            "target_calories",
            "daily_calories",
            "protein_g",
            "carbs_g",
            "fat_g",
        )
        if tdee.get(key) is not None
    }
    if tdee_context:
        context["targets"] = tdee_context

    return context


async def get_meal_insight_user_context(
    event_bus: MealInsightEventBus,
    user_id: str,
) -> dict[str, Any]:
    """Fetch user profile context for insights without making it required."""
    try:
        profile_result = await event_bus.send(GetUserProfileQuery(user_id=user_id))
    except Exception as exc:
        logger.info(
            "meal_value_insights.profile_context_unavailable user_id=%s error=%s",
            user_id,
            type(exc).__name__,
        )
        return {}
    return compact_meal_insight_user_context(profile_result)


async def build_value_insights_for_meal(
    meal,
    *,
    language: str,
    cache_service: CachePort | None,
    ai_manager: MealInsightAIPort,
    user_context: dict[str, Any] | None = None,
):
    """Build/cache meal value insights with optional profile context."""
    return await MealValueInsightService(
        ai_manager=ai_manager,
    ).build_ai(
        dish_name=meal.dish_name,
        nutrition=meal.nutrition,
        ingredient_names_by_id={},
        language=language,
        user_context=user_context or {},
        cache_service=cache_service,
    )


async def build_value_insights_for_meal_with_profile(
    meal,
    *,
    language: str,
    cache_service: CachePort | None,
    ai_manager: MealInsightAIPort,
    event_bus: MealInsightEventBus,
    user_id: str,
):
    """Fetch profile context, then build value insights in the background."""
    user_context = await get_meal_insight_user_context(event_bus, user_id)
    return await build_value_insights_for_meal(
        meal,
        language=language,
        cache_service=cache_service,
        ai_manager=ai_manager,
        user_context=user_context,
    )


def schedule_value_insight_generation(
    task_manager: MealInsightTaskScheduler | None,
    meal,
    *,
    language: str,
    cache_service: CachePort | None,
    ai_manager: MealInsightAIPort | None,
    event_bus: MealInsightEventBus | None,
    user_id: str,
    source: str = "api",
) -> bool:
    """Schedule profile-aware insight generation without blocking meal responses."""
    if (
        cache_service is None
        or task_manager is None
        or ai_manager is None
        or event_bus is None
    ):
        logger.info(
            "meal_value_insights.schedule_skipped source=%s meal_id=%s user_id=%s",
            source,
            getattr(meal, "meal_id", None),
            user_id,
        )
        return False

    task_manager.spawn(
        f"meal-value-insights:{meal.meal_id}",
        build_value_insights_for_meal_with_profile(
            meal,
            language=language,
            cache_service=cache_service,
            ai_manager=ai_manager,
            event_bus=event_bus,
            user_id=user_id,
        ),
    )
    logger.info(
        "meal_value_insights.scheduled source=%s meal_id=%s user_id=%s",
        source,
        meal.meal_id,
        user_id,
    )
    return True
