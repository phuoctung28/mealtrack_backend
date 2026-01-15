"""
CompleteOnboardingCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime

from src.domain.services.timezone_utils import utc_now
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import CompleteOnboardingCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.config import ScopedSession
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(CompleteOnboardingCommand)
class CompleteOnboardingCommandHandler(EventHandler[CompleteOnboardingCommand, Dict[str, Any]]):
    """Handler for marking user onboarding as completed."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: CompleteOnboardingCommand) -> Dict[str, Any]:
        """Mark user onboarding as completed if not already completed."""
        db = ScopedSession()

        try:
            # Find user by firebase_uid
            user = db.query(User).filter(
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
            user.last_accessed = utc_now()

            db.commit()
            await self._invalidate_user_profile(user.id)

            return {
                "firebase_uid": command.firebase_uid,
                "onboarding_completed": True,
                "updated": True,
                "message": "Onboarding marked as completed"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error completing onboarding: {str(e)}")
            raise

    async def _invalidate_user_profile(self, user_id: str):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.user_profile(user_id)
        await self.cache_service.invalidate(cache_key)
