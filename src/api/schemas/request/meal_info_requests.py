"""Request schemas for the meal info generation endpoint."""
from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator


class MealInfoRequest(BaseModel):
    """Request body for POST /v1/meal-info/generate."""

    # Either meal_name or ingredients must be provided
    meal_name: Optional[str] = None
    ingredients: Optional[List[str]] = None

    meal_type: str = "lunch"
    language: str = "en"

    # Optional macros — when all four are present, description is rule-based
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

    @model_validator(mode="after")
    def require_name_or_ingredients(self) -> "MealInfoRequest":
        if not self.meal_name and not self.ingredients:
            raise ValueError("Provide either meal_name or a non-empty ingredients list.")
        if self.ingredients is not None and len(self.ingredients) == 0:
            raise ValueError("ingredients list must not be empty.")
        return self

    @field_validator("meal_type")
    @classmethod
    def validate_meal_type(cls, v: str) -> str:
        valid = {"breakfast", "lunch", "dinner", "snack"}
        if v not in valid:
            raise ValueError(f"meal_type must be one of {sorted(valid)}")
        return v

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None and len(v) > 20:
            raise ValueError("ingredients list cannot exceed 20 items.")
        return v
