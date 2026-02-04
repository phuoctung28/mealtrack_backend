"""RQ task functions for daily meal suggestions."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.api.mappers.daily_meal_mapper import DailyMealMapper
from src.app.commands.daily_meal import (
    GenerateDailyMealSuggestionsCommand,
    GenerateSingleMealCommand,
)
from src.app.queries.daily_meal import (
    GetMealSuggestionsForProfileQuery,
    GetSingleMealForProfileQuery,
)
from src.infra.tasks._rq_async import run_async

logger = logging.getLogger(__name__)


def generate_daily_meal_suggestions_task(
    *,
    user_profile_id: Optional[str],
    request_data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Generate 3-5 daily meal suggestions."""
    logger.info("RQ task: generate_daily_meal_suggestions_task started")

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()

    if user_profile_id:
        query = GetMealSuggestionsForProfileQuery(user_profile_id=user_profile_id)
        result = run_async(event_bus.send(query))
    elif request_data:
        command = GenerateDailyMealSuggestionsCommand(**request_data)
        result = run_async(event_bus.send(command))
    else:
        raise ValueError("Either user_profile_id or request_data must be provided")

    return DailyMealMapper.map_to_suggestions_response(result).model_dump()


def generate_single_daily_meal_task(
    *,
    meal_type: str,
    user_profile_id: Optional[str],
    request_data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a single daily meal suggestion."""
    logger.info("RQ task: generate_single_daily_meal_task started (meal_type=%s)", meal_type)

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()

    if user_profile_id:
        query = GetSingleMealForProfileQuery(
            user_profile_id=user_profile_id,
            meal_type=meal_type,
        )
        result = run_async(event_bus.send(query))
        return {"meal": result["meal"]}

    if request_data:
        command = GenerateSingleMealCommand(meal_type=meal_type, **request_data)
        result = run_async(event_bus.send(command))
        mapped = DailyMealMapper.map_to_single_meal_response(result)
        return mapped

    raise ValueError("Either user_profile_id or request_data must be provided")

