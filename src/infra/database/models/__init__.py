"""
Database models package.

This module imports all database models from their respective submodules
to provide a centralized access point.
"""
# Base models
from .base import BaseMixin, PrimaryEntityMixin, SecondaryEntityMixin
# Conversation models
from .conversation.conversation import Conversation
from .conversation.message import ConversationMessage
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
# Meal models
from .meal.meal import Meal
from .meal.meal_image import MealImage
# Meal planning models
from .meal_planning.meal_plan import MealPlan
from .meal_planning.meal_plan_day import MealPlanDay
from .meal_planning.planned_meal import PlannedMeal
from .nutrition.food_item import FoodItem
# Nutrition models
from .nutrition.nutrition import Nutrition
from .user.profile import UserProfile
# User models
from .user.user import User

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
    
    # Nutrition models
    "Nutrition",
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
]