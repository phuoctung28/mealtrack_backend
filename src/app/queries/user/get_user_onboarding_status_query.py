"""
Query to get user's onboarding status.
"""
from dataclasses import dataclass


@dataclass
class GetUserOnboardingStatusQuery:
    """Query to get user's onboarding status by Firebase UID."""
    firebase_uid: str