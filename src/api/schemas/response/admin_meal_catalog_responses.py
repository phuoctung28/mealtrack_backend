"""Responses for admin meal catalog inspection."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminMealCatalogIngredientResponse(BaseModel):
    display_name: str
    quantity: float
    unit: str


class AdminMealCatalogItemResponse(BaseModel):
    id: str
    catalog_key: str
    name: str
    cuisine: str
    description: str | None = None
    image_url: str | None = None
    meal_types: list[str]
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    ingredient_count: int
    ingredients: list[AdminMealCatalogIngredientResponse]
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminMealCatalogListResponse(BaseModel):
    items: list[AdminMealCatalogItemResponse]
    total: int
    limit: int
    offset: int


class AdminMealCatalogGenerateImageResponse(BaseModel):
    item: AdminMealCatalogItemResponse
    image_url: str
