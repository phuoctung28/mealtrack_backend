"""Meal recommendation domain models."""

from .catalog_recipe import (
    CatalogMeal,
    CatalogMealIngredient,
    MealRecommendationAlternative,
    MealRecommendationInsufficiency,
    MealRecommendationInsufficiencyReason,
    MealRecommendationPlan,
    MealRecommendationSlot,
)
from .meal_recommendation_plan import (
    PersistedMealRecommendationCandidate,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)

__all__ = [
    "CatalogMeal",
    "CatalogMealIngredient",
    "MealRecommendationAlternative",
    "MealRecommendationInsufficiency",
    "MealRecommendationInsufficiencyReason",
    "MealRecommendationPlan",
    "MealRecommendationSlot",
    "PersistedMealRecommendationCandidate",
    "PersistedMealRecommendationPlan",
    "PersistedMealRecommendationSlot",
]
