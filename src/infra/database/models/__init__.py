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
# Notification models
from .notification import NotificationPreferences, UserFcmToken
from .nutrition.food_item import FoodItem
# Nutrition models
from .nutrition.nutrition import Nutrition
from .subscription import Subscription
from .user.profile import UserProfile
# User models
from .user.user import User

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
    
    # Test models
    
    # Notification models
    "NotificationPreferences",
    "UserFcmToken",

    # Food reference (evolved from barcode_products)
    "FoodReferenceModel",
    "BarcodeProductModel",  # backward-compatible alias
]