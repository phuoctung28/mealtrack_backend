"""
UpdateUserLastAccessedCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from datetime import datetime

from src.domain.utils.timezone_utils import utc_now
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user.sync_user_command import UpdateUserLastAccessedCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateUserLastAccessedCommand)
class UpdateUserLastAccessedCommandHandler(EventHandler[UpdateUserLastAccessedCommand, Dict[str, Any]]):
    """Handler for updating user's last accessed timestamp."""

    async def handle(self, command: UpdateUserLastAccessedCommand) -> Dict[str, Any]:
        """Update user's last accessed timestamp."""
        with UnitOfWork() as uow:
            # Find user by firebase_uid
            user = uow.users.find_by_firebase_uid(command.firebase_uid)

            if not user:
                raise ResourceNotFoundException(f"User with Firebase UID {command.firebase_uid} not found")

            # Update last_accessed timestamp
            last_accessed = command.last_accessed or utc_now()
            user.last_accessed = last_accessed
            
            uow.users.save(user)
            # UoW auto-commits on exit

        return {
            "firebase_uid": command.firebase_uid,
            "updated": True,
            "message": "Last accessed timestamp updated successfully",
            "timestamp": last_accessed
        }
