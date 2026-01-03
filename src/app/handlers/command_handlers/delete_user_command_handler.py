"""
DeleteUserCommandHandler - Handler for deleting user accounts.
Performs soft delete in database and hard delete in Firebase Auth.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import DeleteUserCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user import User
from src.infra.services.firebase_auth_service import FirebaseAuthService

logger = logging.getLogger(__name__)


@handles(DeleteUserCommand)
class DeleteUserCommandHandler(EventHandler[DeleteUserCommand, Dict[str, Any]]):
    """Handler for deleting user accounts."""

    def __init__(self, db: Session = None):
        self.db = db
        self.firebase_auth_service = FirebaseAuthService()

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: DeleteUserCommand) -> Dict[str, Any]:
        """
        Delete user account.
        - Soft delete in database (set is_active=False)
        - Anonymize user data
        - Hard delete in Firebase Authentication
        """
        if not self.db:
            raise RuntimeError("Database session not configured")

        try:
            # Find user by firebase_uid
            user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid,
                User.is_active == True  # Only delete active users
            ).first()

            if not user:
                raise ResourceNotFoundException(
                    f"Active user with Firebase UID not found"
                )

            # Store user_id for logging
            user_id = user.id

            # Step 1: Anonymize user data (GDPR compliance)
            user.email = f"deleted_{user.id}@deleted.local"
            user.username = f"deleted_user_{user.id}"
            user.first_name = None
            user.last_name = None
            user.phone_number = None
            user.display_name = None
            user.photo_url = None
            user.password_hash = "DELETED"

            # Step 2: Soft delete in database
            user.is_active = False
            user.last_accessed = datetime.utcnow()

            # Commit database changes first
            self.db.commit()
            logger.info(f"Successfully soft deleted user in database")

            # Step 3: Revoke refresh tokens to invalidate all active sessions
            # This prevents the user from getting new access tokens
            try:
                self.firebase_auth_service.revoke_refresh_tokens(command.firebase_uid)
                logger.info(f"Successfully revoked Firebase refresh tokens")
            except Exception as revoke_error:
                logger.warning(f"Token revocation failed: {str(revoke_error)}")
                # Continue - deletion is more important

            # Step 4: Hard delete from Firebase Authentication
            try:
                firebase_deleted = self.firebase_auth_service.delete_firebase_user(
                    command.firebase_uid
                )
                if firebase_deleted:
                    logger.info(f"Successfully deleted user from Firebase")
                else:
                    logger.warning(f"Firebase deletion returned False")
            except Exception as firebase_error:
                # Log Firebase error but don't rollback DB changes
                logger.error(f"Firebase deletion failed: {str(firebase_error)}")
                # Continue - database soft delete is more important than Firebase cleanup

            return {
                "firebase_uid": command.firebase_uid,
                "deleted": True,
                "message": "Account successfully deleted"
            }

        except ResourceNotFoundException:
            # Re-raise not found errors
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user account: {str(e)}")
            raise Exception(f"Failed to delete user account: {str(e)}")
