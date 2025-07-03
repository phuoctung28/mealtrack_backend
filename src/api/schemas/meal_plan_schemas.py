from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, date
from enum import Enum


class DietaryPreferenceSchema(str, Enum):
    vegan = "vegan"
    vegetarian = "vegetarian"
    pescatarian = "pescatarian"
    gluten_free = "gluten_free"
    keto = "keto"
    paleo = "paleo"
    low_carb = "low_carb"
    dairy_free = "dairy_free"
    none = "none"


class FitnessGoalSchema(str, Enum):
    weight_loss = "weight_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"
    general_health = "general_health"


class MealTypeSchema(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class PlanDurationSchema(str, Enum):
    daily = "daily"
    weekly = "weekly"


class ConversationStateSchema(str, Enum):
    greeting = "greeting"
    asking_dietary_preferences = "asking_dietary_preferences"
    asking_allergies = "asking_allergies"
    asking_fitness_goals = "asking_fitness_goals"
    asking_meal_count = "asking_meal_count"
    asking_plan_duration = "asking_plan_duration"
    asking_cooking_time = "asking_cooking_time"
    asking_cuisine_preferences = "asking_cuisine_preferences"
    confirming_preferences = "confirming_preferences"
    generating_plan = "generating_plan"
    showing_plan = "showing_plan"
    adjusting_meal = "adjusting_meal"
    completed = "completed"


class MessageSchema(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None


class ConversationMessageRequest(BaseModel):
    message: str = Field(..., description="User's message to the meal planning assistant")


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


class UserPreferencesSchema(BaseModel):
    dietary_preferences: List[DietaryPreferenceSchema]
    allergies: List[str]
    fitness_goal: FitnessGoalSchema
    meals_per_day: int = Field(..., ge=1, le=6)
    snacks_per_day: int = Field(default=0, ge=0, le=4)
    cooking_time_weekday: int = Field(..., description="Available cooking time on weekdays in minutes")
    cooking_time_weekend: int = Field(..., description="Available cooking time on weekends in minutes")
    favorite_cuisines: List[str]
    disliked_ingredients: List[str]
    plan_duration: PlanDurationSchema = PlanDurationSchema.weekly


class MealPlanResponse(BaseModel):
    plan_id: str
    user_id: str
    preferences: UserPreferencesSchema
    days: List[DayPlanSchema]
    created_at: datetime
    updated_at: datetime


class MealPlanSummaryResponse(BaseModel):
    plan_id: str
    user_id: str
    plan_duration: PlanDurationSchema
    start_date: date
    end_date: date
    total_meals: int
    created_at: datetime


class ReplaceMealRequest(BaseModel):
    date: date
    meal_id: str
    dietary_preferences: Optional[List[DietaryPreferenceSchema]] = None
    exclude_ingredients: Optional[List[str]] = None
    preferred_cuisine: Optional[str] = None


class ReplaceMealResponse(BaseModel):
    success: bool
    new_meal: PlannedMealSchema
    message: str


class GenerateMealPlanRequest(BaseModel):
    preferences: UserPreferencesSchema


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict] = None