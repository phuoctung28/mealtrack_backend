"""User domain models."""

from .activity import Activity as UserActivity
from .core_user import UserDomainModel, UserProfileDomainModel
from .onboarding import OnboardingSection, OnboardingResponse
from .tdee import (
    TdeeResponse,
    JobType,
    TdeeRequest,
    Sex,
    Goal,
    UnitSystem,
    MacroTargets,
    TrainingLevel,
)
from .user_macros import UserMacros

# Alias for backward compatibility if needed, but explicit is better
TDEE = TdeeResponse

__all__ = [
    "UserActivity",
    "JobType",
    "TrainingLevel",
    "OnboardingSection",
    "OnboardingResponse",
    "TDEE",
    "TdeeResponse",
    "TdeeRequest",
    "Sex",
    "Goal",
    "UnitSystem",
    "MacroTargets",
    "UserMacros",
    "UserDomainModel",
    "UserProfileDomainModel",
]
