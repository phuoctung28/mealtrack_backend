"""RQ task functions for meal plan generation."""

from __future__ import annotations

import logging
from typing import Any

from src.app.commands.meal_plan import GenerateWeeklyIngredientBasedMealPlanCommand
from src.infra.tasks._rq_async import run_async

logger = logging.getLogger(__name__)


def generate_weekly_ingredient_based_meal_plan_task(
    *,
    user_id: str,
    available_ingredients: list[str],
    available_seasonings: list[str],
) -> dict[str, Any]:
    """Generate a weekly ingredient-based meal plan."""
    logger.info(
        "RQ task: generate_weekly_ingredient_based_meal_plan_task started (user_id=%s)",
        user_id,
    )

    from src.api.base_dependencies import initialize_cache_layer

    run_async(initialize_cache_layer())

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()

    command = GenerateWeeklyIngredientBasedMealPlanCommand(
        user_id=user_id,
        available_ingredients=available_ingredients,
        available_seasonings=available_seasonings,
    )

    run_async(event_bus.send(command))

    logger.info(
        "RQ task: generate_weekly_ingredient_based_meal_plan_task finished (user_id=%s)",
        user_id,
    )
    return {
        "success": True,
        "message": "Weekly meal plan generated successfully!",
        "user_id": user_id,
    }

