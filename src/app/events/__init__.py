"""
Event-driven architecture components.
"""

from .base import DomainEvent

# Meal events
from .meal import (
    MealAnalysisStartedEvent,
    MealImageUploadedEvent,
    MealNutritionUpdatedEvent,
    MealEditedEvent,
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
    # Meal events
    "MealAnalysisStartedEvent",
    "MealImageUploadedEvent",
    "MealNutritionUpdatedEvent",
    "MealEditedEvent",
    # TDEE events
    "TdeeCalculatedEvent",
    # User events
    "UserOnboardedEvent",
    "UserProfileUpdatedEvent",
]
