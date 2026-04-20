"""Pydantic models for vision response validation."""
from typing import List, Optional

from pydantic import BaseModel, Field


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
    confidence: float = Field(
        0.5, description="Overall confidence score"
    )
