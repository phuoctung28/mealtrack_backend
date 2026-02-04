"""RQ task functions for meal suggestions."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from src.api.mappers.meal_suggestion_mapper import to_suggestions_list_response
from src.app.commands.meal_suggestion import GenerateMealSuggestionsCommand

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync RQ task."""
    return asyncio.run(coro)


def generate_meal_suggestions_task(
    *,
    user_id: str,
    meal_type: Optional[str],
    meal_portion_type: str,
    ingredients: list[str],
    cooking_time_minutes: int,
    session_id: Optional[str],
    language: str,
    servings: int,
) -> dict[str, Any]:
    """Generate meal suggestions in the RQ worker.

    Returns a JSON-serializable dict.
    """
    logger.info(
        "RQ task: generate_meal_suggestions_task started (user_id=%s, session_id=%s)",
        user_id,
        session_id,
    )

    # Ensure Redis cache layer is initialized in the worker process as well.
    from src.api.base_dependencies import initialize_cache_layer

    _run(initialize_cache_layer())

    # Use the same CQRS/event-bus flow as the synchronous API endpoint.
    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()

    command = GenerateMealSuggestionsCommand(
        user_id=user_id,
        meal_type=meal_type,
        meal_portion_type=meal_portion_type,
        ingredients=ingredients,
        time_available_minutes=cooking_time_minutes,
        session_id=session_id,
        language=language,
        servings=servings,
    )

    session, suggestions = _run(event_bus.send(command))
    response_model = to_suggestions_list_response(session, suggestions)

    logger.info(
        "RQ task: generate_meal_suggestions_task finished (user_id=%s, session_id=%s)",
        user_id,
        session_id,
    )

    return response_model.model_dump()

