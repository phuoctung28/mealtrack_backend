"""
Request schemas for meal suggestion generation.
"""
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class MealSuggestionRequest(BaseModel):
    """
    Request schema for generating meal suggestions.
    
    Generates exactly 3 meal suggestions based on the provided inputs.
    """
    
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ..., 
        description="Type of meal to generate suggestions for"
    )
    ingredients: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Optional list of available ingredients (max 20)"
    )
    time_available_minutes: Optional[int] = Field(
        None,
        gt=0,
        description="Optional time constraint in minutes (Any / <15 / <30 / <60)"
    )
    dietary_preferences: List[str] = Field(
        default_factory=list,
        description="Optional dietary preferences (e.g., vegetarian, vegan, halal)"
    )
    calorie_target: Optional[int] = Field(
        None,
        gt=0,
        description="Optional calorie target for the meal"
    )
    exclude_ids: List[str] = Field(
        default_factory=list,
        description="List of meal IDs to exclude (for regeneration)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "meal_type": "lunch",
                "ingredients": ["chicken breast", "broccoli", "rice"],
                "time_available_minutes": 30,
                "dietary_preferences": ["high-protein"],
                "calorie_target": 500,
                "exclude_ids": []
            }
        }


class SaveMealSuggestionRequest(BaseModel):
    """
    Request schema for saving a selected meal suggestion to meal history.
    """
    
    suggestion_id: str = Field(
        ...,
        description="ID of the suggestion to save"
    )
    name: str = Field(
        ...,
        description="Name of the meal"
    )
    description: str = Field(
        default="",
        description="Description of the meal"
    )
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] = Field(
        ...,
        description="Type of meal"
    )
    estimated_cook_time_minutes: int = Field(
        ...,
        description="Total cooking time in minutes"
    )
    calories: int = Field(
        ...,
        description="Calories for the meal"
    )
    protein: float = Field(
        ...,
        description="Protein in grams"
    )
    carbs: float = Field(
        ...,
        description="Carbohydrates in grams"
    )
    fat: float = Field(
        ...,
        description="Fat in grams"
    )
    ingredients_list: List[str] = Field(
        default_factory=list,
        description="List of ingredients"
    )
    instructions: List[str] = Field(
        default_factory=list,
        description="Cooking instructions"
    )
    meal_date: Optional[str] = Field(
        None,
        description="Date to save the meal for (YYYY-MM-DD format), defaults to today"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "suggestion_id": "meal_lunch_1234",
                "name": "Grilled Chicken with Rice",
                "description": "Healthy high-protein lunch",
                "meal_type": "lunch",
                "estimated_cook_time_minutes": 25,
                "calories": 520,
                "protein": 45.0,
                "carbs": 55.0,
                "fat": 12.0,
                "ingredients_list": ["chicken breast", "brown rice", "broccoli"],
                "instructions": ["Grill chicken", "Cook rice", "Steam broccoli"],
                "meal_date": "2024-01-15"
            }
        }

