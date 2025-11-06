"""
User bounded context - Domain models for user-related data.
"""
from .activity import Activity, ActivityType
from .onboarding import (
    OnboardingSection,
    OnboardingField,
    OnboardingResponse,
    OnboardingSectionType,
    FieldType
)
from .tdee import (
    TdeeRequest,
    TdeeResponse,
    MacroTargets,
    Sex,
    ActivityLevel,
    Goal,
    UnitSystem
)
from .user_macros import UserMacros

__all__ = [
    'Activity',
    'ActivityType',
    'UserMacros',
    'OnboardingSection',
    'OnboardingField',
    'OnboardingResponse',
    'OnboardingSectionType',
    'FieldType',
    'TdeeRequest',
    'TdeeResponse',
    'MacroTargets',
    'Sex',
    'ActivityLevel',
    'Goal',
    'UnitSystem',
]

