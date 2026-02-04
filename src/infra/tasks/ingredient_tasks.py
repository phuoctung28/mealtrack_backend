"""RQ task functions for ingredient recognition."""

from __future__ import annotations

import logging
from typing import Any

from src.app.commands.ingredient import RecognizeIngredientCommand
from src.infra.tasks._rq_async import run_async

logger = logging.getLogger(__name__)


def recognize_ingredient_task(*, image_data: str) -> dict[str, Any]:
    """Recognize an ingredient from a base64 image string."""
    logger.info("RQ task: recognize_ingredient_task started")

    from src.api.dependencies.event_bus import get_configured_event_bus

    event_bus = get_configured_event_bus()
    command = RecognizeIngredientCommand(image_data=image_data)
    result = run_async(event_bus.send(command))
    return result

