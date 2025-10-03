from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from ..common.meal_plan_enums import (
    DietaryPreferenceSchema,
    FitnessGoalSchema,
    PlanDurationSchema
)


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


class ConversationMessageRequest(BaseModel):
    message: str = Field(..., description="User's message to the meal planning assistant")


class ReplaceMealRequest(BaseModel):
    date: date
    meal_id: str
    dietary_preferences: Optional[List[DietaryPreferenceSchema]] = None
    exclude_ingredients: Optional[List[str]] = None
    preferred_cuisine: Optional[str] = None


