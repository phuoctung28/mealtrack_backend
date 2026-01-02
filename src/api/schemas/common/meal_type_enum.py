"""Meal type enum for simplified meal categorization."""

from enum import Enum


class MealTypeEnum(str, Enum):
    """Three meal types replacing 5 T-shirt sizes."""

    SNACK = "snack"  # Fixed ~150-300 kcal
    MAIN = "main"  # Calculated from TDEE ÷ meals_per_day
    OMAD = "omad"  # Full daily target (One Meal A Day)
