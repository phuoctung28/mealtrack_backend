"""RQ task functions for meal image analysis."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from src.api.mappers.meal_mapper import MealMapper
from src.app.commands.meal.upload_meal_image_immediately_command import (
    UploadMealImageImmediatelyCommand,
)
from src.infra.adapters.cloudinary_image_store import CloudinaryImageStore
from src.infra.tasks._rq_async import run_async

logger = logging.getLogger(__name__)


def analyze_meal_image_task(
    *,
    user_id: str,
    file_contents: bytes,
    content_type: str,
    target_date: Optional[str],
    language: str,
    user_description: Optional[str],
) -> dict[str, Any]:
    """Analyze a meal image and return a DetailedMealResponse dict."""
    logger.info("RQ task: analyze_meal_image_task started (user_id=%s)", user_id)

    from src.api.base_dependencies import initialize_cache_layer

    run_async(initialize_cache_layer())

    parsed_target_date = None
    if target_date:
        parsed_target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()

    command = UploadMealImageImmediatelyCommand(
        user_id=user_id,
        file_contents=file_contents,
        content_type=content_type,
        target_date=parsed_target_date,
        language=language,
        user_description=user_description,
    )

    meal = run_async(event_bus.send(command))

    image_url = None
    if meal.image:
        image_store = CloudinaryImageStore()
        image_url = image_store.get_url(meal.image.image_id)

    response = MealMapper.to_detailed_response(meal, image_url, target_language=language)
    logger.info(
        "RQ task: analyze_meal_image_task finished (user_id=%s, meal_id=%s)",
        user_id,
        meal.meal_id,
    )
    return response.model_dump()

