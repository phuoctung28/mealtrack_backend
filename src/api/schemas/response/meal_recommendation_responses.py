"""Responses for durable catalog-backed meal recommendations."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MealRecommendationAlternativeResponse(BaseModel):
    id: str
    recipe_version_id: str
    target_calories: int
    score: float
    position: int


class MealRecommendationSlotResponse(BaseModel):
    id: str
    slot_date: date
    day_index: int
    meal_type: str
    recipe_version_id: str
    target_calories: int
    score: float
    position: int
    version: int
    logged_meal_id: str | None = None
    alternatives: list[MealRecommendationAlternativeResponse]


class MealRecommendationPlanResponse(BaseModel):
    id: str
    status: str
    timezone: str
    start_date: date
    daily_calories: int
    algorithm_version: str
    catalog_release_id: str
    allergy_evaluated: bool
    slots: list[MealRecommendationSlotResponse]
