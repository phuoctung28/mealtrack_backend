"""Pydantic models for legacy vision response validation."""

from pydantic import BaseModel, Field

from src.domain.model.nutrition import MAX_FOOD_ITEM_QUANTITY


class MacrosResponse(BaseModel):
    """Macronutrient data for a food item."""

    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")


class FoodItemResponse(BaseModel):
    """Food item extracted from vision analysis."""

    name: str = Field(..., description="Food item name")
    quantity: float = Field(
        ..., gt=0, le=MAX_FOOD_ITEM_QUANTITY, description="Quantity of food"
    )
    unit: str = Field(..., description="Unit of measurement")
    macros: MacrosResponse = Field(..., description="Macronutrient breakdown")


class VisionAnalyzeResponse(BaseModel):
    """Legacy structured response for vision analysis.

    Invalid AI output must fail validation here. Retry orchestration happens
    before domain mapping, not by silently dropping invalid foods.
    """

    dish_name: str | None = Field(None, description="Dish name")
    is_food: bool = Field(True, description="Whether the image contains edible food")
    foods: list[FoodItemResponse] | None = Field(
        None, max_length=8, description="List of foods"
    )
    confidence: float = Field(0.5, description="Overall confidence score")
