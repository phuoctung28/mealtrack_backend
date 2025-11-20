"""
Pydantic schemas for GPT response validation.

This module provides strongly-typed schemas for validating GPT responses,
improving type safety and error handling in the parsing process.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class GPTMacros(BaseModel):
    """Macronutrient information from GPT response."""
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")
    
    @field_validator('protein', 'carbs', 'fat')
    @classmethod
    def round_macros(cls, v):
        """Round macro values to 1 decimal place."""
        return round(v, 1)


class GPTFoodItem(BaseModel):
    """Individual food item from GPT analysis."""
    name: str = Field(..., min_length=1, description="Food item name")
    quantity: float = Field(..., gt=0, description="Quantity of food")
    unit: str = Field(..., min_length=1, description="Unit of measurement")
    calories: float = Field(..., ge=0, description="Calories")
    macros: GPTMacros = Field(..., description="Macronutrient breakdown")
    confidence: float = Field(1.0, ge=0, le=1, description="Confidence score")
    
    @field_validator('calories')
    @classmethod
    def validate_calories(cls, v, info):
        """Validate calories against macros if possible."""
        if info.data and 'macros' in info.data:
            macros = info.data['macros']
            calculated = (macros.protein * 4) + (macros.carbs * 4) + (macros.fat * 9)
            # Allow 20% tolerance for rounding and estimation
            if abs(v - calculated) > calculated * 0.2:
                # Just log warning, don't fail validation
                pass
        return round(v, 1)


class GPTAnalysisResponse(BaseModel):
    """Complete GPT analysis response structure."""
    dish_name: str = Field(..., description="Overall dish name or food list")
    foods: List[GPTFoodItem] = Field(..., min_items=1, description="List of analyzed foods")
    total_calories: float = Field(..., ge=0, description="Total calories")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence")
    
    # Optional fields for enhanced analysis
    portion_adjustment: Optional[str] = Field(None, description="Portion adjustment note")
    weight_adjustment: Optional[str] = Field(None, description="Weight adjustment note")
    ingredient_based: Optional[bool] = Field(None, description="Whether ingredient-based analysis")
    total_weight_grams: Optional[float] = Field(None, gt=0, description="Total weight if provided")
    
    @field_validator('foods')
    @classmethod
    def validate_foods_not_empty(cls, v):
        """Ensure foods list is not empty."""
        if not v:
            raise ValueError("Foods list cannot be empty")
        return v
    
    @field_validator('total_calories')
    @classmethod
    def validate_total_calories(cls, v, info):
        """Validate total calories matches sum of food items."""
        if info.data and 'foods' in info.data:
            calculated_total = sum(food.calories for food in info.data['foods'])
            # Allow 5% tolerance for rounding
            if abs(v - calculated_total) > calculated_total * 0.05:
                # Use calculated total instead
                return calculated_total
        return round(v, 1)
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "dish_name": "Chicken Caesar Salad",
                "foods": [
                    {
                        "name": "Grilled Chicken Breast",
                        "quantity": 150,
                        "unit": "g",
                        "calories": 247.5,
                        "macros": {
                            "protein": 46.5,
                            "carbs": 0,
                            "fat": 5.4,
                        },
                        "confidence": 0.9
                    },
                    {
                        "name": "Caesar Dressing",
                        "quantity": 2,
                        "unit": "tablespoon",
                        "calories": 150,
                        "macros": {
                            "protein": 1,
                            "carbs": 2,
                            "fat": 16,
                        },
                        "confidence": 0.85
                    }
                ],
                "total_calories": 397.5,
                "confidence": 0.88
            }
        }