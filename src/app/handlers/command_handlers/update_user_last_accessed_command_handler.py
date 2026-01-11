"""
UpdateUserLastAccessedCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime

from src.domain.services.timezone_utils import utc_now
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user.sync_user_command import UpdateUserLastAccessedCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(UpdateUserLastAccessedCommand)
class UpdateUserLastAccessedCommandHandler(EventHandler[UpdateUserLastAccessedCommand, Dict[str, Any]]):
    """Handler for updating user's last accessed timestamp."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: UpdateUserLastAccessedCommand) -> Dict[str, Any]:
        """Update user's last accessed timestamp."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        try:
            # Find user by firebase_uid
            user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()

            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {command.firebase_uid} not found")

            # Update last_accessed timestamp
            last_accessed = command.last_accessed or utc_now()
            user.last_accessed = last_accessed

            self.db.commit()

            return {
                "firebase_uid": command.firebase_uid,
                "updated": True,
                "message": "Last accessed timestamp updated successfully",
                "timestamp": last_accessed
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last accessed: {str(e)}")
            raise
