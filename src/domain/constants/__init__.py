"""
Domain constants and configuration values.

This package centralizes all constants, magic numbers, and configuration
values used throughout the domain layer.
"""

from .languages import (
    DEFAULT_LANGUAGE,
    SUPPORTED_TRANSLATION_LANGUAGES,
    is_supported_language,
    is_supported_translation_pair,
    normalize_language,
)
from .meal_constants import (
    GPTPromptConstants,
    MealDefaults,
    MealDistribution,
    MealPlanningConstants,
    NutritionConstants,
    PortionUnits,
    TDEEConstants,
    WeeklyBudgetConstants,
)

__all__ = [
    "MealDefaults",
    "MealDistribution",
    "NutritionConstants",
    "PortionUnits",
    "GPTPromptConstants",
    "MealPlanningConstants",
    "TDEEConstants",
    "WeeklyBudgetConstants",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_TRANSLATION_LANGUAGES",
    "is_supported_language",
    "is_supported_translation_pair",
    "normalize_language",
]
