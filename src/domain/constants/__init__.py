"""
Domain constants and configuration values.

This package centralizes all constants, magic numbers, and configuration
values used throughout the domain layer.
"""

from .meal_constants import (
    MealDefaults,
    MealDistribution,
    NutritionConstants,
    PortionUnits,
    GPTPromptConstants,
    MealPlanningConstants,
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
]
