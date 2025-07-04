from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, date

from ..common.meal_plan_enums import (
    ConversationStateSchema,
    MealTypeSchema,
    PlanDurationSchema
)
from ..request.meal_plan_requests import UserPreferencesSchema


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


class ReplaceMealResponse(BaseModel):
    success: bool
    new_meal: PlannedMealSchema
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict] = None