"""
Database models package.

This module imports all database models from their respective submodules
to provide a centralized access point.
"""

# Base models
from .base import BaseMixin, PrimaryEntityMixin, SecondaryEntityMixin, TimestampMixin

# Cheat days
from .cheat_day.cheat_day import CheatDayORM

# Enums
from .enums import (
    DietaryPreferenceEnum,
    FitnessGoalEnum,
    GoalEnum,
    JobTypeEnum,
    MealStatusEnum,
    MealTypeEnum,
    PlanDurationEnum,
    SexEnum,
)

# Feature flags
from .feature_flag import FeatureFlag

# Food reference (evolved from barcode_products)
from .food_reference_model import FoodReferenceModel
from .food_reference_nutrient import FoodReferenceNutrientModel
from .food_reference_serving_size import FoodReferenceServingSizeModel
from .hydration_entry import HydrationEntryORM
from .meal.food_item_translation_model import FoodItemTranslationORM

# Meal models
from .meal.meal import MealORM
from .meal.meal_image import MealImageORM
from .meal.meal_instruction_step import MealInstructionStepORM

# Translation models (meals + food items)
from .meal.meal_translation_model import MealTranslationORM
from .meal_image_cache import MealImageCacheModel

# Notification models
from .notification import NotificationORM, NotificationPreferencesORM, UserFcmTokenORM
from .nutrition.food_item import FoodItemORM

# Nutrition models
from .nutrition.nutrition import NutritionORM
from .pending_meal_image_resolution import PendingMealImageResolutionModel

# Saved suggestions
from .saved_suggestion import SavedSuggestionModel
from .saved_suggestion_item import SavedSuggestionItemModel
from .saved_suggestion_step import SavedSuggestionStepModel
from .subscription import Subscription
from .user.profile import UserProfile
from .user.profile_preference import UserProfilePreference

# User models
from .user.user import User

# Weekly budgets
from .weekly.weekly_macro_budget import WeeklyMacroBudgetORM

# Backward-compatible alias
BarcodeProductModel = FoodReferenceModel

# Referral system
# Email log
from .email_log import EmailLog

# Movement tracking
from .movement_entry import MovementEntryORM

# Promo codes (email marketing)
from .promo_code import PromoCode, PromoCodeRedemption
from .referral import PayoutRequest, ReferralCode, ReferralConversion, ReferralWallet

# Weight tracking
from .weight_entry import WeightEntryORM

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
    "UserProfilePreference",
    "Subscription",
    # Nutrition models
    "NutritionORM",
    "FoodItemORM",
    # Meal models
    "MealORM",
    "MealImageORM",
    "MealInstructionStepORM",
    "MealTranslationORM",
    "FoodItemTranslationORM",
    # Test models
    # Notification models
    "NotificationORM",
    "NotificationPreferencesORM",
    "UserFcmTokenORM",
    # Feature flags
    "FeatureFlag",
    # Saved suggestions
    "SavedSuggestionModel",
    "SavedSuggestionItemModel",
    "SavedSuggestionStepModel",
    # Weekly budgets
    "WeeklyMacroBudgetORM",
    # Cheat days
    "CheatDayORM",
    # Food reference (evolved from barcode_products)
    "FoodReferenceModel",
    "FoodReferenceNutrientModel",
    "FoodReferenceServingSizeModel",
    "BarcodeProductModel",  # backward-compatible alias
    "HydrationEntryORM",
    "MealImageCacheModel",
    "PendingMealImageResolutionModel",
    # Referral system
    "ReferralCode",
    "ReferralConversion",
    "ReferralWallet",
    "PayoutRequest",
    # Weight tracking
    "WeightEntryORM",
    # Movement tracking
    "MovementEntryORM",
    # Email log
    "EmailLog",
    # Promo codes
    "PromoCode",
    "PromoCodeRedemption",
]
