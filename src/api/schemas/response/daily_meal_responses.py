"""
Daily meal suggestion response DTOs.
"""
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class MealTypeEnum(str, Enum):
    """Enum for meal types."""
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class NutritionTotalsResponse(BaseModel):
    """Response DTO for nutrition totals."""
    calories: float = Field(..., ge=0, description="Total calories")
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")
    
    class Config:
        json_schema_extra = {
            "example": {
                "calories": 2500.0,
                "protein": 125.0,
                "carbs": 300.0,
                "fat": 83.0
            }
        }


class SuggestedMealResponse(BaseModel):
    """Response DTO for a suggested meal."""
    meal_id: str = Field(..., description="Unique meal identifier")
    meal_type: MealTypeEnum = Field(..., description="Type of meal")
    name: str = Field(..., description="Meal name")
    description: str = Field(..., description="Meal description")
    
    # Time information
    prep_time: int = Field(..., ge=0, description="Preparation time in minutes")
    cook_time: int = Field(..., ge=0, description="Cooking time in minutes")
    total_time: int = Field(..., ge=0, description="Total time in minutes")
    
    # Nutrition information
    calories: float = Field(..., ge=0, description="Calories")
    protein: float = Field(..., ge=0, description="Protein in grams")
    carbs: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat: float = Field(..., ge=0, description="Fat in grams")
    
    # Recipe information
    ingredients: List[str] = Field(..., min_items=1, description="List of ingredients")
    instructions: List[str] = Field(..., min_items=1, description="Cooking instructions")
    
    # Dietary information
    is_vegetarian: bool = Field(..., description="Is vegetarian")
    is_vegan: bool = Field(..., description="Is vegan")
    is_gluten_free: bool = Field(..., description="Is gluten-free")
    cuisine_type: Optional[str] = Field(None, description="Cuisine type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "meal_id": "123e4567-e89b-12d3-a456-426614174000",
                "meal_type": "breakfast",
                "name": "Protein-Packed Oatmeal",
                "description": "High-protein oatmeal with berries and nuts",
                "prep_time": 5,
                "cook_time": 10,
                "total_time": 15,
                "calories": 450.0,
                "protein": 25.0,
                "carbs": 55.0,
                "fat": 15.0,
                "ingredients": [
                    "1 cup rolled oats",
                    "1 scoop protein powder",
                    "1/2 cup mixed berries",
                    "2 tablespoons almond butter"
                ],
                "instructions": [
                    "Cook oats according to package directions",
                    "Stir in protein powder",
                    "Top with berries and almond butter"
                ],
                "is_vegetarian": True,
                "is_vegan": False,
                "is_gluten_free": False,
                "cuisine_type": "American"
            }
        }


class DailyMealSuggestionsResponse(BaseModel):
    """Response DTO for daily meal suggestions."""
    date: str = Field(..., description="Date for the suggestions (ISO format)")
    meal_count: int = Field(..., ge=0, description="Number of meals suggested")
    meals: List[SuggestedMealResponse] = Field(..., description="List of suggested meals")
    daily_totals: NutritionTotalsResponse = Field(..., description="Total nutrition for all suggested meals")
    target_totals: NutritionTotalsResponse = Field(..., description="Target nutrition based on user goals")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "meal_count": 4,
                "meals": [],  # Would contain SuggestedMealResponse objects
                "daily_totals": {
                    "calories": 2450.0,
                    "protein": 122.0,
                    "carbs": 295.0,
                    "fat": 82.0
                },
                "target_totals": {
                    "calories": 2500.0,
                    "protein": 125.0,
                    "carbs": 300.0,
                    "fat": 83.0
                }
            }
        }


class SingleMealSuggestionResponse(BaseModel):
    """Response DTO for a single meal suggestion."""
    meal: SuggestedMealResponse = Field(..., description="Suggested meal details")


class MealSuggestionErrorResponse(BaseModel):
    """Response DTO for meal suggestion errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(None, description="Additional error details")


class UserMealPlanSummaryResponse(BaseModel):
    """Response DTO for user meal plan summary."""
    user_profile_id: str = Field(..., description="User profile ID")
    total_suggestions_generated: int = Field(..., ge=0, description="Total suggestions generated")
    average_daily_calories: float = Field(..., ge=0, description="Average daily calories")
    preferred_meal_types: List[str] = Field(..., description="Most suggested meal types")
    common_ingredients: List[str] = Field(..., description="Most common ingredients")
    dietary_compliance: Dict[str, bool] = Field(..., description="Dietary preference compliance")


class QuickMealIdeaResponse(BaseModel):
    """Response DTO for a quick meal idea with enriched data."""
    meal_id: str = Field(..., description="Unique meal identifier")
    name: str = Field(..., description="Meal name")
    description: str = Field(..., description="Short tagline (10 words max)")
    time_minutes: int = Field(..., ge=0, description="Total cooking time in minutes")
    calories: int = Field(..., ge=0, description="Estimated calories")
    protein_g: float = Field(..., ge=0, description="Protein in grams")
    carbs_g: float = Field(..., ge=0, description="Carbohydrates in grams")
    fat_g: float = Field(..., ge=0, description="Fat in grams")
    pairs_with: List[str] = Field(
        default_factory=list,
        description="3-5 complementary ingredients"
    )
    quick_recipe: List[str] = Field(
        default_factory=list,
        description="4-6 simple cooking steps"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags like 'quick', 'high-protein'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "meal_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Chicken Stir-Fry",
                "description": "Quick, flavorful, pairs with rice",
                "time_minutes": 15,
                "calories": 420,
                "protein_g": 35.0,
                "carbs_g": 25.0,
                "fat_g": 18.0,
                "pairs_with": ["avocado", "lemon", "cherry tomatoes", "feta cheese"],
                "quick_recipe": [
                    "Season chicken with salt and pepper",
                    "Heat pan with olive oil over high heat",
                    "Stir-fry chicken until golden (5 min)",
                    "Add vegetables and sauce",
                    "Serve immediately"
                ],
                "tags": ["quick", "high-protein", "low-carb"]
            }
        }


class QuickMealSuggestionsResponse(BaseModel):
    """Response DTO for quick meal suggestions."""
    success: bool = Field(True, description="Whether generation was successful")
    meal_type: str = Field(..., description="Type of meal requested")
    ingredients: List[str] = Field(..., description="Ingredients used in search")
    time_filter: Optional[str] = Field(None, description="Time filter applied")
    meals: List[QuickMealIdeaResponse] = Field(..., description="List of meal ideas")
    displayed_count: int = Field(..., ge=0, description="Number of meals currently displayed")
    total_count: int = Field(..., ge=0, description="Total number of meals available")
    has_more: bool = Field(False, description="Whether more meals are available")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "meal_type": "lunch",
                "ingredients": ["chicken"],
                "time_filter": "quick",
                "meals": [],
                "displayed_count": 3,
                "total_count": 6,
                "has_more": True
            }
        }