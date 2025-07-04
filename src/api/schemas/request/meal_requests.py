"""
Meal-related request DTOs.
"""
from typing import Optional

from pydantic import BaseModel, Field


class MacrosRequest(BaseModel):
    """Request DTO for macronutrient information."""
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams") 
    fat: float = Field(..., ge=0, description="Fat in grams")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in grams")


class CreateMealRequest(BaseModel):
    """Request DTO for creating a meal manually."""
    name: str = Field(..., min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, le=5000, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosRequest] = Field(None, description="Macros per 100g")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Grilled Chicken Breast",
                "description": "Seasoned with herbs and olive oil",
                "weight_grams": 150,
                "calories_per_100g": 165,
                "macros_per_100g": {
                    "protein": 31.0,
                    "carbs": 0,
                    "fat": 3.6
                }
            }
        }


class UpdateMealRequest(BaseModel):
    """Request DTO for updating meal information."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Meal name")
    description: Optional[str] = Field(None, max_length=500, description="Meal description")
    weight_grams: Optional[float] = Field(None, gt=0, le=5000, description="Weight in grams")
    calories_per_100g: Optional[float] = Field(None, ge=0, description="Calories per 100g")
    macros_per_100g: Optional[MacrosRequest] = Field(None, description="Macros per 100g")


class UpdateMealMacrosRequest(BaseModel):
    """Request DTO for updating meal portion size."""
    weight_grams: float = Field(
        ..., 
        gt=0, 
        le=5000, 
        description="Weight of the meal portion in grams"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "weight_grams": 250.0
            }
        }


class MealSearchRequest(BaseModel):
    """Request DTO for searching meals."""
    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    include_ingredients: bool = Field(False, description="Include ingredients in search")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "chicken",
                "limit": 20,
                "include_ingredients": True
            }
        }


class AnalyzeMealImageRequest(BaseModel):
    """Request DTO for meal image analysis options."""
    immediate_analysis: bool = Field(
        False, 
        description="Perform immediate analysis (synchronous)"
    )
    portion_size_grams: Optional[float] = Field(
        None,
        gt=0,
        le=5000,
        description="Known portion size in grams"
    )
    context: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional context for analysis"
    )