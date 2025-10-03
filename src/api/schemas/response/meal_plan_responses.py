from datetime import datetime, date
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from ..common.meal_plan_enums import (
    MealTypeSchema,
    PlanDurationSchema
)


class PlannedMealSchema(BaseModel):
    meal_id: str
    meal_type: MealTypeSchema
    name: str
    description: str
    prep_time: int = Field(..., description="Preparation time in minutes")
    cook_time: int = Field(..., description="Cooking time in minutes")
    total_time: int = Field(..., description="Total time in minutes")
    calories: int
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")
    ingredients: List[str]
    seasonings: List[str]
    instructions: List[str]
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    cuisine_type: Optional[str] = None


class DayPlanSchema(BaseModel):
    date: date
    meals: List[PlannedMealSchema]
    total_nutrition: Dict[str, float] = Field(..., description="Total daily nutrition values")


class MealPlanSummaryResponse(BaseModel):
    plan_id: str
    user_id: str
    plan_duration: PlanDurationSchema
    start_date: date
    end_date: date
    total_meals: int
    created_at: datetime


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict] = None


class NutritionSummarySchema(BaseModel):
    calories: int
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")


class UserPreferenceSummarySchema(BaseModel):
    dietary_preferences: List[str]
    health_conditions: List[str]
    allergies: List[str]
    activity_level: str
    fitness_goal: str
    meals_per_day: int
    snacks_per_day: int


class MealsByDateResponse(BaseModel):
    """Response for getting meals by specific date."""
    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    day_formatted: str = Field(..., description="Human-readable date format (e.g., 'Monday, January 15, 2024')")
    meals: List[PlannedMealSchema] = Field(..., description="List of meals for this date")
    total_meals: int = Field(..., description="Total number of meals for this date")
    user_id: str = Field(..., description="User ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "day_formatted": "Monday, January 15, 2024",
                "meals": [
                    {
                        "meal_id": "meal_001",
                        "meal_type": "breakfast",
                        "name": "Greek Yogurt Parfait",
                        "description": "Healthy breakfast with berries and granola",
                        "prep_time": 5,
                        "cook_time": 0,
                        "total_time": 5,
                        "calories": 350,
                        "protein": 20.5,
                        "carbs": 35.2,
                        "fat": 12.8,
                        "ingredients": ["Greek yogurt", "Mixed berries", "Granola", "Honey"],
                        "instructions": ["Layer yogurt in bowl", "Add berries", "Top with granola"],
                        "is_vegetarian": True,
                        "is_vegan": False,
                        "is_gluten_free": True,
                        "cuisine_type": "Mediterranean"
                    }
                ],
                "total_meals": 1,
                "user_id": "user123"
            }
        }


# New strongly typed response models for meal generation
class GeneratedMealResponse(BaseModel):
    """Response model for a generated meal (strongly typed version)."""
    meal_id: str = Field(..., description="Unique meal identifier")
    meal_type: str = Field(..., description="Type of meal (breakfast, lunch, dinner, snack)")
    name: str = Field(..., description="Name of the meal")
    description: str = Field(..., description="Brief description of the meal")
    prep_time: int = Field(..., description="Preparation time in minutes")
    cook_time: int = Field(..., description="Cooking time in minutes")
    total_time: int = Field(..., description="Total time (prep + cook) in minutes")
    calories: int = Field(..., description="Calories for this meal")
    protein: float = Field(..., description="Protein in grams")
    carbs: float = Field(..., description="Carbohydrates in grams")
    fat: float = Field(..., description="Fat in grams")
    ingredients: List[str] = Field(..., description="List of ingredients")
    instructions: List[str] = Field(..., description="Cooking instructions")
    is_vegetarian: bool = Field(..., description="Whether meal is vegetarian")
    is_vegan: bool = Field(..., description="Whether meal is vegan")
    is_gluten_free: bool = Field(..., description="Whether meal is gluten-free")
    cuisine_type: Optional[str] = Field(None, description="Type of cuisine")


class UserPreferencesStrongResponse(BaseModel):
    """User preferences in the response (strongly typed version)."""
    dietary_preferences: List[str] = Field(default=[], description="Dietary preferences")
    health_conditions: List[str] = Field(default=[], description="Health conditions")
    allergies: List[str] = Field(default=[], description="Food allergies")
    activity_level: str = Field(..., description="Activity level")
    fitness_goal: str = Field(..., description="Fitness goal")
    meals_per_day: int = Field(..., description="Number of meals per day")
    snacks_per_day: int = Field(..., description="Number of snacks per day")




    class Config:
        """Pydantic config."""
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class MealPlanGenerationStatusResponse(BaseModel):
    """Simple status response for meal plan generation operations."""
    success: bool = Field(..., description="Whether the meal plan generation was successful")
    message: str = Field(..., description="Status message for the user")
    user_id: str = Field(..., description="User identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Weekly meal plan generated successfully!",
                "user_id": "user123"
            }
        }
