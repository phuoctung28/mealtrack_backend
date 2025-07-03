from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date
from enum import Enum
from src.domain.model.macro_targets import SimpleMacroTargets


class MealTypeEnum(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class UserPreferencesRequest(BaseModel):
    """User preferences from onboarding data"""
    age: int = Field(..., ge=13, le=120, description="User age")
    gender: str = Field(..., description="User gender (male/female/other)")
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    activity_level: str = Field(..., description="Activity level (sedentary/lightly_active/moderately_active/very_active/extra_active)")
    goal: str = Field(..., description="Fitness goal (lose_weight/maintain_weight/gain_weight/build_muscle)")
    dietary_preferences: Optional[List[str]] = Field(default=[], description="Dietary preferences/restrictions")
    health_conditions: Optional[List[str]] = Field(default=[], description="Health conditions")
    target_calories: Optional[float] = Field(None, description="Daily calorie target (will be calculated if not provided)")
    target_macros: Optional[SimpleMacroTargets] = Field(None, description="Daily macro targets (will be calculated if not provided)")


class SuggestedMealSchema(BaseModel):
    """Schema for a suggested meal"""
    meal_id: str
    meal_type: str
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


class NutritionTotalsSchema(BaseModel):
    """Schema for nutrition totals"""
    calories: float
    protein: float
    carbs: float
    fat: float
    
    @classmethod
    def from_macro_targets(cls, macros: SimpleMacroTargets, calories: float) -> "NutritionTotalsSchema":
        """Create from SimpleMacroTargets instance"""
        return cls(
            calories=calories,
            protein=macros.protein,
            carbs=macros.carbs,
            fat=macros.fat
        )


class DailyMealSuggestionsResponse(BaseModel):
    """Response for daily meal suggestions"""
    date: str = Field(..., description="Date for the suggestions (ISO format)")
    meal_count: int = Field(..., description="Number of meals suggested")
    meals: List[SuggestedMealSchema] = Field(..., description="List of suggested meals")
    daily_totals: NutritionTotalsSchema = Field(..., description="Total nutrition for all suggested meals")
    target_totals: NutritionTotalsSchema = Field(..., description="Target nutrition based on user goals")


class SingleMealSuggestionResponse(BaseModel):
    """Response for single meal suggestion"""
    meal: SuggestedMealSchema


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    message: str
    details: Optional[Dict] = None