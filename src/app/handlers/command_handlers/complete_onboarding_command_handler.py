"""
CompleteOnboardingCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import CompleteOnboardingCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(CompleteOnboardingCommand)
class CompleteOnboardingCommandHandler(EventHandler[CompleteOnboardingCommand, Dict[str, Any]]):
    """Handler for marking user onboarding as completed."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: CompleteOnboardingCommand) -> Dict[str, Any]:
        """Mark user onboarding as completed if not already completed."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        try:
            # Find user by firebase_uid
            user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()

            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {command.firebase_uid} not found")

            # Check if onboarding is already completed
            if user.onboarding_completed:
                return {
                    "firebase_uid": command.firebase_uid,
                    "onboarding_completed": True,
                    "updated": False,
                    "message": "Onboarding already completed"
                }

            # Set onboarding as completed
            user.onboarding_completed = True
            user.last_accessed = datetime.utcnow()

            self.db.commit()

            return {
                "firebase_uid": command.firebase_uid,
                "onboarding_completed": True,
                "updated": True,
                "message": "Onboarding marked as completed"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing onboarding: {str(e)}")
            raise
