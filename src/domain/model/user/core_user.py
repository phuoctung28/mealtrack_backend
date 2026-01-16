"""
Domain models for User and UserProfile.

These models are plain Python objects that represent the core business logic
and are independent of the database or any other infrastructure.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from src.domain.model.auth.auth_provider import AuthProvider
from src.domain.model.base import BaseDomainModel


@dataclass(kw_only=True)
class UserProfileDomainModel(BaseDomainModel):
    """Domain model for a user's profile."""
    user_id: UUID
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: str
    fitness_goal: str
    meals_per_day: int
    is_current: bool = True
    body_fat_percentage: Optional[float] = None
    target_weight_kg: Optional[float] = None
    snacks_per_day: int = 1
    dietary_preferences: List[str] = field(default_factory=list)
    health_conditions: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)


@dataclass(kw_only=True)
class UserDomainModel(BaseDomainModel):
    """Domain model for a User."""
    firebase_uid: str
    email: str
    username: str
    password_hash: str
    provider: AuthProvider
    is_active: bool = True
    onboarding_completed: bool = False
    last_accessed: datetime = field(default_factory=datetime.now)
    timezone: str = 'UTC'
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    profiles: List[UserProfileDomainModel] = field(default_factory=list)

    @property
    def current_profile(self) -> Optional[UserProfileDomainModel]:
        """Get the current active profile."""
        return next((p for p in self.profiles if p.is_current), None)

    def is_premium(self) -> bool:
        """
        Check if user has active premium subscription.
        Note: This is a placeholder as subscription is not yet a domain model.
        """
        return False