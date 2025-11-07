"""Firebase Authentication Service for user management operations."""
import logging
from typing import Optional

import firebase_admin.auth
from firebase_admin import auth
from firebase_admin.auth import UserNotFoundError

logger = logging.getLogger(__name__)


class FirebaseAuthService:
    """Service for managing Firebase Authentication users."""

    @staticmethod
    def delete_firebase_user(firebase_uid: str) -> bool:
        """
        Delete a user from Firebase Authentication.

        Args:
            firebase_uid: The Firebase UID of the user to delete

        Returns:
            bool: True if deletion was successful, False otherwise

        Raises:
            Exception: If an unexpected error occurs during deletion
        """
        try:
            auth.delete_user(firebase_uid)
            logger.info(f"Successfully deleted Firebase user")
            return True

        except UserNotFoundError:
            logger.warning(f"Firebase user not found - may have been already deleted")
            # User already deleted is considered a success for idempotency
            return True

        except Exception as e:
            logger.error(f"Failed to delete Firebase user: {str(e)}")
            raise Exception(f"Failed to delete user from Firebase: {str(e)}")

    @staticmethod
    def get_firebase_user(firebase_uid: str) -> Optional[auth.UserRecord]:
        """
        Get a user from Firebase Authentication.

        Args:
            firebase_uid: The Firebase UID of the user

        Returns:
            Optional[auth.UserRecord]: The user record if found, None otherwise
        """
        try:
            return auth.get_user(firebase_uid)
        except UserNotFoundError:
            logger.warning(f"Firebase user not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get Firebase user: {str(e)}")
            return None

    @staticmethod
    def verify_firebase_user_exists(firebase_uid: str) -> bool:
        """
        Check if a user exists in Firebase Authentication.

        Args:
            firebase_uid: The Firebase UID to check

        Returns:
            bool: True if user exists, False otherwise
        """
        user = FirebaseAuthService.get_firebase_user(firebase_uid)
        return user is not None
