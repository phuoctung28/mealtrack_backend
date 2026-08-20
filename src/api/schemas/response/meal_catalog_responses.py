"""Public authenticated meal-catalog browse responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.api.schemas.response.meal_recommendation_responses import (
    MealRecommendationCatalogMealResponse,
)


class MealCatalogItemResponse(MealRecommendationCatalogMealResponse):
    """Catalog item using the recommendation detail nutrition contract."""

    meal_types: list[str]
    ingredient_count: int


class MealCatalogListResponse(BaseModel):
    items: list[MealCatalogItemResponse]
    total: int
    limit: int
    offset: int
    feed: Literal["popular", "for_you"]
    ranking_source: Literal["curated", "personalized"]
    fallback: bool = False
    allergy_evaluated: bool = False
