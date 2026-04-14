"""
Database models package.

This module imports all database models from their respective submodules
to provide a centralized access point.
"""
# Base models
from .base import BaseMixin, PrimaryEntityMixin, SecondaryEntityMixin, TimestampMixin
# Enums
from .enums import (
    MealStatusEnum,
    DietaryPreferenceEnum,
    FitnessGoalEnum,
    MealTypeEnum,
    PlanDurationEnum,
    JobTypeEnum,
    SexEnum,
    GoalEnum,
)
# Meal models
from .meal.meal import Meal
from .meal.meal_image import MealImage
# Translation models (meals + food items)
from .meal.meal_translation_model import MealTranslation
from .meal.food_item_translation_model import FoodItemTranslation
# Notification models
from .notification import NotificationPreferences, NotificationSentLog, UserFcmToken
from .nutrition.food_item import FoodItem
# Nutrition models
from .nutrition.nutrition import Nutrition
from .subscription import Subscription
from .user.profile import UserProfile
# User models
from .user.user import User

# Feature flags
from .feature_flag import FeatureFlag

# Saved suggestions
from .saved_suggestion import SavedSuggestionModel

# Weekly budgets
from .weekly.weekly_macro_budget import WeeklyMacroBudget

# Cheat days
from .cheat_day.cheat_day import CheatDay

# Food reference (evolved from barcode_products)
from .food_reference_model import FoodReferenceModel
# Backward-compatible alias
BarcodeProductModel = FoodReferenceModel

__all__ = [
    # Base
    "BaseMixin",
    "PrimaryEntityMixin", 
    "SecondaryEntityMixin",
    "TimestampMixin",
    
    # Enums
    "MealStatusEnum",
    "DietaryPreferenceEnum",
    "FitnessGoalEnum",
    "MealTypeEnum",
    "PlanDurationEnum",
    "JobTypeEnum",
    "SexEnum",
    "GoalEnum",
    
    # User models
    "User",
    "UserProfile",
    "Subscription",
    
    # Nutrition models
    "Nutrition",
    "FoodItem",
    
    # Meal models
    "Meal",
    "MealImage",
    "MealTranslation",
    "FoodItemTranslation",
    
    # Test models
    
    # Notification models
    "NotificationPreferences",
    "NotificationSentLog",
    "UserFcmToken",

    # Feature flags
    "FeatureFlag",

    # Saved suggestions
    "SavedSuggestionModel",

    # Weekly budgets
    "WeeklyMacroBudget",

    # Cheat days
    "CheatDay",

    # Food reference (evolved from barcode_products)
    "FoodReferenceModel",
    "BarcodeProductModel",  # backward-compatible alias
]