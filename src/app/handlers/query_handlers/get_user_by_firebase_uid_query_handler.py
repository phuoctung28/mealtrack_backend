"""
GetUserByFirebaseUidQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
import os
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.user.get_user_by_firebase_uid_query import GetUserByFirebaseUidQuery
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(GetUserByFirebaseUidQuery)
class GetUserByFirebaseUidQueryHandler(EventHandler[GetUserByFirebaseUidQuery, Dict[str, Any]]):
    """Handler for getting user by Firebase UID."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, query: GetUserByFirebaseUidQuery) -> Dict[str, Any]:
        """Get user by Firebase UID."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        # Get user by firebase_uid
        user = self.db.query(User).filter(
            User.firebase_uid == query.firebase_uid
        ).first()

        if not user:
            raise ResourceNotFoundException(f"User with Firebase UID {query.firebase_uid} not found")

        # In development, avoid touching subscriptions table (may not exist yet)
        if os.getenv("ENVIRONMENT") == "development":
            is_premium_value = True
        else:
            try:
                is_premium_value = bool(user.is_premium())
            except Exception:
                # Safe fallback if subscription lookup fails
                is_premium_value = False

        return {
            "id": user.id,
            "firebase_uid": user.firebase_uid,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "display_name": user.display_name,
            "photo_url": user.photo_url,
            "provider": user.provider,
            "is_active": user.is_active,
            "onboarding_completed": user.onboarding_completed,
            "last_accessed": user.last_accessed,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            # Required by UserProfileResponse
            "is_premium": is_premium_value
        }
