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
from .meal_recommendation_plan import (
    PersistedMealRecommendationAlternative,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
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
    "PersistedMealRecommendationAlternative",
    "PersistedMealRecommendationPlan",
    "PersistedMealRecommendationSlot",
]
