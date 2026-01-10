"""
UpdateUserLastAccessedCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user.sync_user_command import UpdateUserLastAccessedCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.config import ScopedSession
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(UpdateUserLastAccessedCommand)
class UpdateUserLastAccessedCommandHandler(EventHandler[UpdateUserLastAccessedCommand, Dict[str, Any]]):
    """Handler for updating user's last accessed timestamp."""

    async def handle(self, command: UpdateUserLastAccessedCommand) -> Dict[str, Any]:
        """Update user's last accessed timestamp."""
        db = ScopedSession()

        try:
            # Find user by firebase_uid
            user = db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()

            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {command.firebase_uid} not found")

            # Update last_accessed timestamp
            last_accessed = command.last_accessed or datetime.utcnow()
            user.last_accessed = last_accessed

            db.commit()

            return {
                "firebase_uid": command.firebase_uid,
                "updated": True,
                "message": "Last accessed timestamp updated successfully",
                "timestamp": last_accessed
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating last accessed: {str(e)}")
            raise
