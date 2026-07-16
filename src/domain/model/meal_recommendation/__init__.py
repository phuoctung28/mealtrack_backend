"""Meal recommendation domain models."""

from .catalog_recipe import (
    CatalogRecipeIngredient,
    CatalogRecipeVersion,
    CatalogRelease,
    MealRecommendationAlternative,
    MealRecommendationInsufficiency,
    MealRecommendationInsufficiencyReason,
    MealRecommendationPlan,
    MealRecommendationSlot,
)

__all__ = [
    "CatalogRecipeIngredient",
    "CatalogRecipeVersion",
    "CatalogRelease",
    "MealRecommendationAlternative",
    "MealRecommendationInsufficiency",
    "MealRecommendationInsufficiencyReason",
    "MealRecommendationPlan",
    "MealRecommendationSlot",
]
