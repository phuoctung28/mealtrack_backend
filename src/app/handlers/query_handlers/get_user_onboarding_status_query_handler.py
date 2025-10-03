"""
GetUserOnboardingStatusQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.user.get_user_by_firebase_uid_query import GetUserOnboardingStatusQuery
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(GetUserOnboardingStatusQuery)
class GetUserOnboardingStatusQueryHandler(EventHandler[GetUserOnboardingStatusQuery, Dict[str, Any]]):
    """Handler for getting user's onboarding status by Firebase UID."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, query: GetUserOnboardingStatusQuery) -> Dict[str, Any]:
        """Get user's onboarding status by Firebase UID."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user by firebase_uid
        user = self.db.query(User).filter(
            User.firebase_uid == query.firebase_uid
        ).first()

        if not user:
            raise ResourceNotFoundException(f"User with Firebase UID {query.firebase_uid} not found")

        return {
            "firebase_uid": user.firebase_uid,
            "onboarding_completed": user.onboarding_completed,
            "is_active": user.is_active,
            "last_accessed": user.last_accessed
        }
