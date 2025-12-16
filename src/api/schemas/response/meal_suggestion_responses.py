"""
Response schemas for meal suggestion generation.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class MacrosSchema(BaseModel):
    """Macronutrient information."""
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class MealSuggestionItem(BaseModel):
    """
    A single meal suggestion with all required information.
    """
    
    id: str = Field(..., description="Unique identifier for this suggestion")
    name: str = Field(..., description="Name of the meal")
    description: str = Field(..., description="Brief description of the meal")
    estimated_cook_time_minutes: int = Field(
        ..., 
        description="Total cooking time (prep + cook) in minutes"
    )
    calories: int = Field(..., description="Total calories for the meal")
    macros: MacrosSchema = Field(..., description="Macronutrient breakdown")
    ingredients_list: List[str] = Field(
        ..., 
        description="List of ingredients with portions"
    )
    instructions: List[str] = Field(
        default_factory=list,
        description="Step-by-step cooking instructions"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags like vegetarian, vegan, gluten-free, cuisine type"
    )
    image_url: Optional[str] = Field(
        None,
        description="Optional image URL for the meal"
    )
    source: Optional[str] = Field(
        None,
        description="Optional source of the recipe"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "meal_lunch_1234",
                "name": "Grilled Chicken with Rice",
                "description": "Healthy high-protein lunch with lean chicken and brown rice",
                "estimated_cook_time_minutes": 25,
                "calories": 520,
                "macros": {
                    "protein": 45.0,
                    "carbs": 55.0,
                    "fat": 12.0
                },
                "ingredients_list": [
                    "200g chicken breast",
                    "150g brown rice",
                    "100g broccoli",
                    "1 tbsp olive oil"
                ],
                "instructions": [
                    "Season chicken breast with salt and pepper",
                    "Grill chicken for 6-7 minutes per side",
                    "Cook brown rice according to package instructions",
                    "Steam broccoli for 5 minutes",
                    "Serve together"
                ],
                "tags": ["high-protein", "gluten-free", "healthy"],
                "image_url": None,
                "source": "AI Generated"
            }
        }


class MealSuggestionsResponse(BaseModel):
    """
    Response containing exactly 3 meal suggestions.
    """
    
    request_id: str = Field(
        ..., 
        description="Unique identifier for this request (for tracking)"
    )
    suggestions: List[MealSuggestionItem] = Field(
        ..., 
        min_length=3,
        max_length=3,
        description="Exactly 3 meal suggestions"
    )
    generation_token: str = Field(
        ...,
        description="Token for regeneration tracking (to avoid duplicates)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123",
                "suggestions": [
                    {
                        "id": "meal_lunch_1234",
                        "name": "Grilled Chicken with Rice",
                        "description": "Healthy high-protein lunch",
                        "estimated_cook_time_minutes": 25,
                        "calories": 520,
                        "macros": {"protein": 45.0, "carbs": 55.0, "fat": 12.0},
                        "ingredients_list": ["chicken breast", "rice", "broccoli"],
                        "instructions": ["Grill chicken", "Cook rice"],
                        "tags": ["high-protein", "gluten-free"]
                    }
                ],
                "generation_token": "gen_xyz789"
            }
        }


class SaveMealSuggestionResponse(BaseModel):
    """
    Response after saving a meal suggestion to history.
    """
    
    success: bool = Field(..., description="Whether the save was successful")
    message: str = Field(..., description="Status message")
    meal_id: Optional[str] = Field(
        None,
        description="ID of the saved meal in the database"
    )
    meal_date: str = Field(
        ...,
        description="Date the meal was saved for (YYYY-MM-DD)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Meal suggestion saved successfully to your meal history",
                "meal_id": "12345",
                "meal_date": "2024-01-15"
            }
        }

