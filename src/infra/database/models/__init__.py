"""
Database models package.

This module imports all database models from their respective submodules
to provide a centralized access point.
"""
# Base models
from .base import BaseMixin, PrimaryEntityMixin, SecondaryEntityMixin

# Enums
from .enums import (
    MealStatusEnum,
    DietaryPreferenceEnum,
    FitnessGoalEnum,
    MealTypeEnum,
    PlanDurationEnum,
    ConversationStateEnum,
    ActivityLevelEnum,
    SexEnum,
    GoalEnum,
)

# User models
from .user.user import User
from .user.profile import UserProfile
from .user.preferences import UserPreference, UserDietaryPreference, UserHealthCondition, UserAllergy
from .user.goals import UserGoal

# Nutrition models
from .nutrition.nutrition import Nutrition
from .nutrition.macros import Macros
from .nutrition.food_item import FoodItem

# Meal models
from .meal.meal import Meal
from .meal.meal_image import MealImage

# Meal planning models
from .meal_planning.meal_plan import MealPlan
from .meal_planning.meal_plan_day import MealPlanDay
from .meal_planning.planned_meal import PlannedMeal

# Conversation models
from .conversation.conversation import Conversation
from .conversation.message import ConversationMessage

# Other models (keep as-is for now)
from .tdee_calculation import TdeeCalculation

__all__ = [
    # Base
    "BaseMixin",
    "PrimaryEntityMixin", 
    "SecondaryEntityMixin",
    
    # Enums
    "MealStatusEnum",
    "DietaryPreferenceEnum",
    "FitnessGoalEnum",
    "MealTypeEnum",
    "PlanDurationEnum",
    "ConversationStateEnum",
    "ActivityLevelEnum",
    "SexEnum",
    "GoalEnum",
    
    # User models
    "User",
    "UserProfile",
    "UserPreference",
    "UserDietaryPreference",
    "UserHealthCondition",
    "UserAllergy",
    "UserGoal",
    
    # Nutrition models
    "Nutrition",
    "Macros",
    "FoodItem",
    
    # Meal models
    "Meal",
    "MealImage",
    
    # Meal planning models
    "MealPlan",
    "MealPlanDay",
    "PlannedMeal",
    
    # Conversation models
    "Conversation",
    "ConversationMessage",
    
    # Other models
    "TdeeCalculation",
]