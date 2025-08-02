"""
Request schemas for ingredient-based meal plan generation.
"""
from typing import List
from pydantic import BaseModel, Field


class IngredientBasedMealPlanRequest(BaseModel):
    """
    Simplified request schema for generating meal plans based on available ingredients.
    
    All other preferences (dietary restrictions, nutrition targets, meal planning preferences)
    are automatically retrieved from the user's profile.
    """
    
    # Only ingredient data - everything else comes from user profile
    available_ingredients: List[str] = Field(
        ..., 
        min_items=1,
        description="List of available ingredient names (e.g., ['chicken breast', 'broccoli', 'rice'])"
    )
    available_seasonings: List[str] = Field(
        default_factory=list,
        description="List of available seasonings and spices (e.g., ['salt', 'pepper', 'garlic'])"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "available_ingredients": [
                    "chicken breast",
                    "broccoli", 
                    "brown rice",
                    "olive oil",
                    "onions"
                ],
                "available_seasonings": [
                    "salt", "black pepper", "garlic powder", "paprika", "thyme"
                ]
            }
        } 