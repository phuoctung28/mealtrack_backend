from datetime import datetime, date
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from ..common.meal_plan_enums import (
    ConversationStateSchema,
    MealTypeSchema,
    PlanDurationSchema
)


class MessageSchema(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None


class ConversationMessageResponse(BaseModel):
    conversation_id: str
    state: ConversationStateSchema
    assistant_message: str
    requires_input: bool = Field(default=True, description="Whether the assistant expects a response")
    meal_plan_id: Optional[str] = Field(None, description="ID of generated meal plan if available")


class StartConversationResponse(BaseModel):
    conversation_id: str
    state: ConversationStateSchema
    assistant_message: str


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    state: ConversationStateSchema
    messages: List[MessageSchema]
    context: Dict
    created_at: datetime
    updated_at: datetime


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


class ReplaceMealResponse(BaseModel):
    success: bool
    new_meal: PlannedMealSchema
    message: str


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


class DailyMealPlanResponse(BaseModel):
    user_id: str
    date: str = Field(..., description="Date of the meal plan (e.g., 'today')")
    meals: List[PlannedMealSchema]
    total_nutrition: NutritionSummarySchema
    target_nutrition: NutritionSummarySchema
    user_preferences: UserPreferenceSummarySchema
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "date": "today",
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
                "total_nutrition": {
                    "calories": 2100,
                    "protein": 120.5,
                    "carbs": 250.2,
                    "fat": 85.8
                },
                "target_nutrition": {
                    "calories": 2200,
                    "protein": 125.0,
                    "carbs": 275.0,
                    "fat": 85.0
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


class DailyMealPlanStrongResponse(BaseModel):
    """Response model for a daily meal plan (strongly typed version)."""
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date of the meal plan (ISO format)")
    plan_id: Optional[str] = Field(None, description="Plan identifier if saved")
    meals: List[GeneratedMealResponse] = Field(..., description="List of generated meals")
    total_nutrition: NutritionSummarySchema = Field(..., description="Total nutrition for the day")
    target_nutrition: NutritionSummarySchema = Field(..., description="Target nutrition goals")
    user_preferences: UserPreferencesStrongResponse = Field(..., description="User preferences used")

    class Config:
        """Pydantic config."""
        json_encoders = {
            date: lambda v: v.isoformat()
        }
