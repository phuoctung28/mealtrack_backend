"""Shared post-commit meal translation persistence."""

from __future__ import annotations

import logging

from src.domain.model.meal import Meal
from src.domain.services.meal_analysis.meal_translation_service import (
    MealTranslationService,
)

logger = logging.getLogger(__name__)


async def persist_meal_translation(
    service: MealTranslationService | None,
    meal: Meal,
    language: str | None,
) -> None:
    """Persist localized meal translation so Today's Meals can show titles."""

    normalized = (language or "en").strip().lower()
    if normalized == "en" or service is None:
        return

    nutrition = getattr(meal, "nutrition", None)
    food_items = list(getattr(nutrition, "food_items", None) or [])
    dish_name = getattr(meal, "dish_name", None) or ""
    if not dish_name and not food_items:
        return

    try:
        await service.translate_meal(
            meal=meal,
            dish_name=dish_name,
            food_items=food_items,
            target_language=normalized,
        )
    except Exception as exc:
        logger.warning(
            "meal translation failed meal=%s language=%s error_type=%s",
            meal.meal_id,
            normalized,
            type(exc).__name__,
        )
