"""Meal recommendation command handlers."""

from .create_three_day_meal_recommendation_command_handler import (
    CreateThreeDayMealRecommendationCommandHandler,
)
from .log_recommended_meal_command_handler import LogRecommendedMealCommandHandler
from .swap_meal_recommendation_slot_command_handler import (
    SwapMealRecommendationSlotCommandHandler,
)

__all__ = [
    "CreateThreeDayMealRecommendationCommandHandler",
    "SwapMealRecommendationSlotCommandHandler",
    "LogRecommendedMealCommandHandler",
]
