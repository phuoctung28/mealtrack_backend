"""
SyncUserCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from src.app.commands.user.sync_user_command import SyncUserCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.models.user import User

logger = logging.getLogger(__name__)


@handles(SyncUserCommand)
class SyncUserCommandHandler(EventHandler[SyncUserCommand, Dict[str, Any]]):
    """Handler for syncing user data from Firebase authentication."""

    def __init__(self, db: Session = None):
        self.db = db

    def set_dependencies(self, db: Session):
        """Set dependencies for dependency injection."""
        self.db = db

    async def handle(self, command: SyncUserCommand) -> Dict[str, Any]:
        """Sync user data from Firebase authentication."""
        if not self.db:
            raise RuntimeError("Database session not configured")

        try:
            # Check if user exists by firebase_uid
            existing_user = self.db.query(User).filter(
                User.firebase_uid == command.firebase_uid
            ).first()

            created = False
            updated = False

            if existing_user:
                # Update existing user
                updated = self._update_existing_user(existing_user, command)
                user = existing_user
                logger.info('Updated existing user')
            else:
                # Create new user
                user = self._create_new_user(command)
                created = True
                logger.info('Created new user')

            # Commit changes
            self.db.commit()
            self.db.refresh(user)

            # Prepare response
            return {
                "user": {
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
                    "updated_at": user.updated_at
                },
                "created": created,
                "updated": updated,
                "message": "User created successfully" if created else "User updated successfully" if updated else "User data up to date"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing user data: {str(e)}")
            raise

    def _create_new_user(self, command: SyncUserCommand) -> User:
        """Create a new user from Firebase data."""
        # Generate username if not provided
        username = command.username or self._generate_username(command.email, command.display_name)

        # Ensure username is unique
        username = self._ensure_unique_username(username)

        # Extract names if not provided
        first_name, last_name = self._extract_names(command.display_name, command.first_name, command.last_name)

        # Create new user
        user = User(
            firebase_uid=command.firebase_uid,
            email=command.email,
            username=username,
            password_hash="",  # No password for Firebase users
            first_name=first_name,
            last_name=last_name,
            phone_number=command.phone_number,
            display_name=command.display_name,
            photo_url=command.photo_url,
            provider=command.provider,
            is_active=True,
            onboarding_completed=False,
        )

        self.db.add(user)
        return user

    def _update_existing_user(self, user: User, command: SyncUserCommand) -> bool:
        """Update existing user with new Firebase data."""
        updated = False

        # Update fields that might have changed
        if user.email != command.email:
            user.email = command.email
            updated = True

        if user.phone_number != command.phone_number:
            user.phone_number = command.phone_number
            updated = True

        if user.display_name != command.display_name:
            user.display_name = command.display_name
            updated = True

        if user.photo_url != command.photo_url:
            user.photo_url = command.photo_url
            updated = True

        if user.provider != command.provider:
            user.provider = command.provider
            updated = True

        # Always update last_accessed
        user.last_accessed = datetime.utcnow()
        updated = True

        return updated

    def _generate_username(self, email: str, display_name: str = None) -> str:
        """Generate a username from email or display name."""
        if display_name:
            # Use display name, remove spaces and special characters
            username = re.sub(r'[^a-zA-Z0-9]', '', display_name.lower())
        else:
            # Use email prefix
            username = email.split('@')[0]
            username = re.sub(r'[^a-zA-Z0-9]', '', username.lower())

        # Ensure minimum length
        if len(username) < 3:
            username = f"user{username}"

        # Limit length
        return username[:20]

    def _ensure_unique_username(self, base_username: str) -> str:
        """Ensure username is unique by appending numbers if needed."""
        username = base_username
        counter = 1

        while self.db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
            # Prevent infinite loop
            if counter > 999:
                username = f"{base_username}{datetime.utcnow().microsecond}"
                break

        return username

    def _extract_names(self, display_name: str = None, first_name: str = None, last_name: str = None):
        """Extract first and last names from display name or provided names."""
        if first_name and last_name:
            return first_name, last_name

        if display_name:
            name_parts = display_name.strip().split()
            if len(name_parts) >= 2:
                return name_parts[0], ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                return name_parts[0], None

        return first_name, last_name
