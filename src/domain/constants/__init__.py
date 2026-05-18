"""
Domain constants and configuration values.

This package centralizes all constants, magic numbers, and configuration
values used throughout the domain layer.
"""

from .meal_constants import (
    MealDistribution,
    NutritionConstants,
    PortionUnits,
    GPTPromptConstants,
    MealPlanningConstants,
    TDEEConstants,
    WeeklyBudgetConstants,
)
from .met_table import MET_TABLE, estimate_burn

__all__ = [
    "MealDistribution",
    "NutritionConstants",
    "PortionUnits",
    "GPTPromptConstants",
    "MealPlanningConstants",
    "TDEEConstants",
    "WeeklyBudgetConstants",
    "MET_TABLE",
    "estimate_burn",
]
