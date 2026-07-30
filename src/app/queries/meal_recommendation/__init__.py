"""Meal recommendation queries."""

from .get_meal_recommendation_plan_query import GetMealRecommendationPlanQuery
from .get_meal_recommendation_slot_detail_query import (
    GetMealRecommendationSlotDetailQuery,
)

__all__ = [
    "GetMealRecommendationPlanQuery",
    "GetMealRecommendationSlotDetailQuery",
]
