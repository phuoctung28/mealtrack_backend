"""
Response schemas for weekly meal plan generation.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WeeklyMealResponse(BaseModel):
    """Response for a single meal in the weekly plan."""
    day: str = Field(..., description="Day of the week (Monday, Tuesday, etc.)")
    meal_type: str = Field(..., description="Type of meal (breakfast, lunch, dinner, snack)")
    name: str = Field(..., description="Name of the meal")
    description: str = Field(..., description="Brief description of the meal")
    prep_time: int = Field(..., description="Preparation time in minutes")
    cook_time: int = Field(..., description="Cooking time in minutes")
    calories: int = Field(..., description="Calories per serving")
    protein: float = Field(..., description="Protein content in grams")
    carbs: float = Field(..., description="Carbohydrate content in grams")
    fat: float = Field(..., description="Fat content in grams")
    ingredients: List[str] = Field(..., description="List of ingredients")
    instructions: List[str] = Field(..., description="Cooking instructions")
    is_vegetarian: bool = Field(..., description="Whether the meal is vegetarian")
    is_vegan: bool = Field(..., description="Whether the meal is vegan")
    is_gluten_free: bool = Field(..., description="Whether the meal is gluten-free")
    cuisine_type: str = Field(..., description="Type of cuisine")


class NutritionInfo(BaseModel):
    """Nutrition information."""
    calories: int = Field(..., description="Total calories")
    protein: float = Field(..., description="Total protein in grams")
    carbs: float = Field(..., description="Total carbohydrates in grams")
    fat: float = Field(..., description="Total fat in grams")


class UserPreferencesResponse(BaseModel):
    """User preferences used for meal planning."""
    dietary_preferences: List[str] = Field(..., description="Dietary restrictions and preferences")
    health_conditions: List[str] = Field(..., description="Health conditions")
    allergies: List[str] = Field(..., description="Food allergies")
    activity_level: str = Field(..., description="Activity level")
    fitness_goal: str = Field(..., description="Fitness goal")
    meals_per_day: int = Field(..., description="Number of meals per day")
    snacks_per_day: int = Field(..., description="Number of snacks per day")


class WeeklyMealPlanResponse(BaseModel):
    """Response for weekly meal plan generation."""
    user_id: str = Field(..., description="User ID")
    plan_type: str = Field(..., description="Type of plan (weekly)")
    start_date: str = Field(..., description="Start date of the plan (Monday)")
    end_date: str = Field(..., description="End date of the plan (Sunday)")
    days: Dict[str, List[WeeklyMealResponse]] = Field(..., description="Meals organized by day")
    meals: List[WeeklyMealResponse] = Field(..., description="All meals in the plan")
    total_nutrition: NutritionInfo = Field(..., description="Total nutrition for the entire week")
    daily_average_nutrition: NutritionInfo = Field(..., description="Average daily nutrition")
    target_nutrition: NutritionInfo = Field(..., description="Target nutrition goals")
    user_preferences: UserPreferencesResponse = Field(..., description="User preferences used")
    plan_id: Optional[str] = Field(None, description="Database plan ID if saved")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "plan_type": "weekly",
                "start_date": "2024-01-15",
                "end_date": "2024-01-21",
                "days": {
                    "Monday": [
                        {
                            "day": "Monday",
                            "meal_type": "breakfast",
                            "name": "Protein Oatmeal Bowl",
                            "description": "Hearty oatmeal with protein powder and fruits",
                            "prep_time": 5,
                            "cook_time": 5,
                            "calories": 450,
                            "protein": 25.0,
                            "carbs": 55.0,
                            "fat": 15.0,
                            "ingredients": ["60g rolled oats", "30g protein powder", "1 medium banana"],
                            "instructions": ["Cook oats with water", "Stir in protein powder"],
                            "is_vegetarian": True,
                            "is_vegan": False,
                            "is_gluten_free": False,
                            "cuisine_type": "International"
                        }
                    ]
                },
                "meals": [],
                "total_nutrition": {
                    "calories": 14000,
                    "protein": 875.0,
                    "carbs": 1750.0,
                    "fat": 490.0
                },
                "daily_average_nutrition": {
                    "calories": 2000,
                    "protein": 125.0,
                    "carbs": 250.0,
                    "fat": 70.0
                },
                "target_nutrition": {
                    "calories": 2000,
                    "protein": 150.0,
                    "carbs": 250.0,
                    "fat": 70.0
                },
                "user_preferences": {
                    "dietary_preferences": ["vegetarian"],
                    "health_conditions": [],
                    "allergies": ["nuts"],
                    "activity_level": "moderate",
                    "fitness_goal": "maintenance",
                    "meals_per_day": 3,
                    "snacks_per_day": 1
                }
            }
        } 