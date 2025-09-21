"""
Event-driven architecture components.
"""
from .base import DomainEvent

# Daily meal events
from .daily_meal import (
    DailyMealsGeneratedEvent,
)

# Meal events
from .meal import (
    MealAnalysisStartedEvent,
    MealImageUploadedEvent,
    MealNutritionUpdatedEvent,
    MealEditedEvent,
)

# Meal plan events
from .meal_plan import (
    ConversationStartedEvent,
    MealPlanGeneratedEvent,
    MealReplacedEvent,
)

# TDEE events
from .tdee import (
    TdeeCalculatedEvent,
)

# User events
from .user import (
    UserOnboardedEvent,
    UserProfileUpdatedEvent,
)

__all__ = [
    # Base
    "DomainEvent",
    
    # Daily meal events
    "DailyMealsGeneratedEvent",
    
    # Meal events
    "MealAnalysisStartedEvent",
    "MealImageUploadedEvent",
    "MealNutritionUpdatedEvent",
    "MealEditedEvent",

    # Meal plan events
    "ConversationStartedEvent",
    "MealPlanGeneratedEvent",
    "MealReplacedEvent",
    
    # TDEE events
    "TdeeCalculatedEvent",
    
    # User events
    "UserOnboardedEvent",
    "UserProfileUpdatedEvent",
]