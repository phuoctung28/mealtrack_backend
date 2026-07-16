"""Meal recommendation catalog database models."""

from .catalog_recipe import (
    CatalogRecipeIngredientORM,
    CatalogRecipeMealTypeORM,
    CatalogRecipeORM,
    CatalogRecipeRightsRecordORM,
    CatalogRecipeSourceORM,
    CatalogRecipeVersionORM,
    CatalogReleaseORM,
)
from .meal_recommendation_plan import (
    MealRecommendationPlanORM,
    MealRecommendationSlotAlternativeORM,
    MealRecommendationSlotORM,
)

__all__ = [
    "CatalogRecipeIngredientORM",
    "CatalogRecipeMealTypeORM",
    "CatalogRecipeORM",
    "CatalogRecipeRightsRecordORM",
    "CatalogRecipeSourceORM",
    "CatalogRecipeVersionORM",
    "CatalogReleaseORM",
    "MealRecommendationPlanORM",
    "MealRecommendationSlotAlternativeORM",
    "MealRecommendationSlotORM",
]
