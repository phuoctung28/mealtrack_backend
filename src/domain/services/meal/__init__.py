"""Meal domain services."""
from .meal_core_service import MealCoreService
from .meal_fallback_service import MealFallbackService

__all__ = ["MealCoreService", "MealFallbackService"]
