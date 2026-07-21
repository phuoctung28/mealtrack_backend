"""Responses for durable catalog-backed meal recommendations."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class MealRecommendationMacrosResponse(BaseModel):
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    sugar_g: float


class MealRecommendationIngredientResponse(BaseModel):
    food_reference_id: int
    display_name: str
    quantity: float
    unit: str


class MealRecommendationCatalogMealResponse(BaseModel):
    id: str
    name: str
    cuisine: str
    description: str | None = None
    image_url: str | None = None
    calories: int
    macros: MealRecommendationMacrosResponse
    ingredients: list[MealRecommendationIngredientResponse]


class MealRecommendationCatalogMealSummaryResponse(BaseModel):
    id: str
    name: str
    cuisine: str
    image_url: str | None = None
    calories: int
    macros: MealRecommendationMacrosResponse


class MealRecommendationAlternativeResponse(BaseModel):
    id: str
    catalog_meal_id: str
    catalog_meal: MealRecommendationCatalogMealResponse
    score: float
    candidate_rank: int


class MealRecommendationSlotSummaryResponse(BaseModel):
    id: str
    slot_date: date
    day_index: int
    meal_type: str
    catalog_meal_id: str
    catalog_meal: MealRecommendationCatalogMealSummaryResponse
    target_calories: int
    position: int
    selection_version: int
    logged_meal_id: str | None = None


class MealRecommendationSlotResponse(BaseModel):
    id: str
    slot_date: date
    day_index: int
    meal_type: str
    catalog_meal_id: str
    catalog_meal: MealRecommendationCatalogMealResponse
    target_calories: int
    score: float
    position: int
    selection_version: int
    logged_meal_id: str | None = None
    alternatives: list[MealRecommendationAlternativeResponse]


class MealRecommendationPlanSummaryResponse(BaseModel):
    id: str
    status: str
    timezone: str
    start_date: date
    daily_calories: int
    allergy_evaluated: bool = False
    slots: list[MealRecommendationSlotSummaryResponse]


class MealRecommendationSlotDetailResponse(BaseModel):
    plan_id: str
    slot: MealRecommendationSlotResponse


class MealRecommendationPlanResponse(BaseModel):
    id: str
    status: str
    timezone: str
    start_date: date
    daily_calories: int
    allergy_evaluated: bool = False
    slots: list[MealRecommendationSlotResponse]
