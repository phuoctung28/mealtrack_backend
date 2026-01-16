"""
GetUserOnboardingStatusQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.user.get_user_onboarding_status_query import GetUserOnboardingStatusQuery
from src.infra.database.models.user import User
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetUserOnboardingStatusQuery)
class GetUserOnboardingStatusQueryHandler(EventHandler[GetUserOnboardingStatusQuery, Dict[str, Any]]):
    """Handler for getting user's onboarding status by Firebase UID."""

    async def handle(self, query: GetUserOnboardingStatusQuery) -> Dict[str, Any]:
        """Get user's onboarding status by Firebase UID."""
        with UnitOfWork() as uow:
            # Get user by firebase_uid using the UnitOfWork session
            user = (
                uow.session.query(User)
                .filter(User.firebase_uid == query.firebase_uid)
                .first()
            )

            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {query.firebase_uid} not found")

            return {
                "firebase_uid": user.firebase_uid,
                "onboarding_completed": user.onboarding_completed,
                "is_active": user.is_active,
                "last_accessed": user.last_accessed,
            }
