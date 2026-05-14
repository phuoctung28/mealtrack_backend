"""Pydantic models for vision response validation."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class MacrosResponse(BaseModel):
    """Macronutrient data for a food item."""

    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")


class FoodItemResponse(BaseModel):
    """Food item extracted from vision analysis."""

    name: str = Field(..., description="Food item name")
    quantity: float = Field(..., gt=0, description="Quantity of food")
    unit: str = Field(..., description="Unit of measurement")
    macros: MacrosResponse = Field(..., description="Macronutrient breakdown")


class VisionAnalyzeResponse(BaseModel):
    """Structured response for vision analysis."""

    dish_name: Optional[str] = Field(None, description="Dish name")
    foods: Optional[List[FoodItemResponse]] = Field(
        None, max_items=8, description="List of foods"
    )
    confidence: float = Field(0.5, description="Overall confidence score")

    @model_validator(mode="before")
    @classmethod
    def drop_zero_quantity_foods(cls, values: Any) -> Any:
        """Strip food items with quantity <= 0 before field-level validation.

        GPT occasionally returns quantity=0 for trace ingredients. Removing
        them here prevents a ValidationError from propagating to the caller.
        """
        if not isinstance(values, dict):
            return values
        foods = values.get("foods")
        if isinstance(foods, list):
            values["foods"] = [
                f for f in foods
                if not isinstance(f, dict)
                or "quantity" not in f  # missing field → let Pydantic reject it
                or _coerce_quantity(f["quantity"]) > 0  # present but <= 0 → drop silently
            ]
        return values


def _coerce_quantity(raw: Any) -> float:
    """Return the numeric value of a quantity field, or 0.0 if not parseable."""
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0
