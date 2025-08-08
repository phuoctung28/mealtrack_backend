"""
Command to mark user onboarding as completed.
"""
from dataclasses import dataclass
from src.app.events.base import Command


@dataclass
class CompleteOnboardingCommand(Command):
    """Command to mark user onboarding as completed."""
    firebase_uid: str