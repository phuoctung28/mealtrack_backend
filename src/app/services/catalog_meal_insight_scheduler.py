"""Warm generic meal-value insights when catalog recipes are imported."""

from __future__ import annotations

import logging

from src.app.services.meal_value_insight_scheduler import build_value_insights_for_meal
from src.domain.constants.languages import SUPPORTED_TRANSLATION_LANGUAGES
from src.domain.model.meal_recommendation import CatalogMeal
from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.ports.cache_port import CachePort
from src.domain.ports.meal_insight_ai_port import MealInsightAIPort

logger = logging.getLogger(__name__)


class _CatalogInsightMeal:
    def __init__(self, catalog_meal: CatalogMeal) -> None:
        self.meal_id = catalog_meal.id
        self.dish_name = catalog_meal.name
        self.nutrition = Nutrition(
            macros=Macros(
                protein=float(catalog_meal.protein_g),
                carbs=float(catalog_meal.carbs_g),
                fat=float(catalog_meal.fat_g),
                fiber=float(catalog_meal.fiber_g),
                sugar=float(catalog_meal.sugar_g),
            ),
            food_items=[
                FoodItem(
                    id=str(ingredient.food_reference_id),
                    name=ingredient.display_name,
                    quantity=float(ingredient.quantity),
                    unit=ingredient.unit,
                    macros=Macros(protein=0, carbs=0, fat=0, fiber=0, sugar=0),
                    food_reference_id=ingredient.food_reference_id,
                )
                for ingredient in catalog_meal.ingredients
            ],
        )


def schedule_catalog_import_insights(
    task_manager,
    meals: list[CatalogMeal],
    *,
    cache_service: CachePort | None,
    ai_manager: MealInsightAIPort | None,
    languages: frozenset[str] = SUPPORTED_TRANSLATION_LANGUAGES,
) -> int:
    """Queue generic (non-profile) insights for newly imported catalog meals."""

    if task_manager is None or cache_service is None or ai_manager is None:
        logger.info("catalog_import_insights.skipped meals=%s", len(meals))
        return 0

    scheduled = 0
    for catalog_meal in meals:
        meal = _CatalogInsightMeal(catalog_meal)
        for language in languages:
            task_manager.spawn(
                f"catalog-meal-insights:{catalog_meal.id}:{language}",
                build_value_insights_for_meal(
                    meal,
                    language=language,
                    cache_service=cache_service,
                    ai_manager=ai_manager,
                    user_context={},
                ),
            )
            scheduled += 1
    logger.info(
        "catalog_import_insights.scheduled meals=%s tasks=%s",
        len(meals),
        scheduled,
    )
    return scheduled
