"""
SyncUserCommandHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional

from src.domain.utils.timezone_utils import utc_now
from src.app.commands.user.sync_user_command import SyncUserCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.infra.database.uow import UnitOfWork
from src.domain.model.user import UserDomainModel
from src.domain.model.notification import NotificationPreferences
from src.domain.model.auth.auth_provider import AuthProvider

logger = logging.getLogger(__name__)


@handles(SyncUserCommand)
class SyncUserCommandHandler(EventHandler[SyncUserCommand, Dict[str, Any]]):
    """Handler for syncing user data from Firebase authentication."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, command: SyncUserCommand) -> Dict[str, Any]:
        """Sync user data from Firebase authentication."""
        # Use provided UoW or create default
        uow = self.uow or UnitOfWork()

        # Using 'with uow' manages the transaction scope
        with uow:
            try:
                # Check if user exists by firebase_uid
                existing_user = uow.users.find_by_firebase_uid(command.firebase_uid)

                created = False
                updated = False
                user = None

                if existing_user:
                    # Update existing user
                    updated = self._update_existing_user(existing_user, command)
                    user = uow.users.save(existing_user)
                    logger.info('Updated existing user')
                else:
                    # Create new user
                    user = self._create_new_user(command, uow)
                    # Save user to get ID
                    user = uow.users.save(user)
                    created = True
                    logger.info('Created new user')

                    # Create default notification preferences
                    self._create_default_notification_preferences(user.id, uow)

                # Commit transaction
                uow.commit()

                # Get subscription info from UoW
                subscription_info = None
                active_subscription = uow.subscriptions.find_active_by_user_id(str(user.id))
                is_premium = active_subscription is not None
                
                if active_subscription:
                    subscription_info = {
                        "product_id": active_subscription.product_id,
                        "status": active_subscription.status,
                        "expires_at": active_subscription.expires_at.isoformat() if active_subscription.expires_at else None,
                        "platform": active_subscription.platform,
                        "is_monthly": active_subscription.product_id.endswith("_monthly") if active_subscription.product_id else False,
                        "is_yearly": active_subscription.product_id.endswith("_yearly") if active_subscription.product_id else False,
                    }
                
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
                        # "created_at": user.created_at, # created_at might be None in pure domain if not set
                        "is_premium": is_premium,
                        "subscription": subscription_info
                    },
                    "created": created,
                    "updated": updated,
                    "message": "User created successfully" if created else "User updated successfully" if updated else "User data up to date"
                }

            except Exception as e:
                uow.rollback()
                logger.error(f"Error syncing user data: {str(e)}")
                raise

    def _create_new_user(self, command: SyncUserCommand, uow: UnitOfWorkPort) -> UserDomainModel:
        """Create a new user domain model from Firebase data."""
        # Generate username if not provided
        username = command.username or self._generate_username(command.email, command.display_name)

        # Ensure username is unique (this logic requires repo support, simulating for now or skipping check)
        # Real impl would check uow.users.find_by_username(username)
        # username = self._ensure_unique_username(username, uow) 

        # Extract names if not provided
        first_name, last_name = self._extract_names(command.display_name, command.first_name, command.last_name)

        # Create new user domain model
        return UserDomainModel(
            firebase_uid=command.firebase_uid,
            email=command.email,
            username=username,
            password_hash="",  # No password for Firebase users
            first_name=first_name,
            last_name=last_name,
            phone_number=command.phone_number,
            display_name=command.display_name,
            photo_url=command.photo_url,
            provider=AuthProvider.from_string(command.provider),
            is_active=True,
            onboarding_completed=False,
        )

    def _update_existing_user(self, user: UserDomainModel, command: SyncUserCommand) -> bool:
        """Update existing user with new Firebase data."""
        updated = False

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

        # Provider update logic?
        
        # Always update last_accessed
        user.last_accessed = utc_now()
        # updated = True # Logic says always updated if accessed? Maybe separation is better.

        return updated

    def _generate_username(self, email: str, display_name: str = None) -> str:
        """Generate a username from email or display name."""
        if display_name:
            username = re.sub(r'[^a-zA-Z0-9]', '', display_name.lower())
        else:
            username = email.split('@')[0]
            username = re.sub(r'[^a-zA-Z0-9]', '', username.lower())

        if len(username) < 3:
            username = f"user{username}"

        return username[:20]

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
    
    def _create_default_notification_preferences(self, user_id: Any, uow: UnitOfWorkPort):
        """Create default notification preferences using repository."""
        if not user_id:
            logger.warning("Cannot create notification preferences: user_id is None")
            return
        
        # Create default preferences domain model
        # Using string ID for user_id because domain model uses UUID but repo handles string conversion if needed?
        # UserDomainModel.id is UUID. NotificationPreferences.user_id is str (from previous check).
        # Let's ensure type compatibility.
        user_id_str = str(user_id)
        
        default_prefs = NotificationPreferences.create_default(user_id_str)
        uow.notifications.save_notification_preferences(default_prefs)
        logger.info(f"Added default notification preferences for user {user_id}")