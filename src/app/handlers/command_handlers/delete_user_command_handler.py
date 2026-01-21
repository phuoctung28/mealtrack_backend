"""
DeleteUserCommandHandler - Handler for deleting user accounts.
Performs soft delete in database and hard delete in Firebase Auth.
"""
import logging
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import DeleteUserCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.uow import UnitOfWork
from src.infra.services.firebase_auth_service import FirebaseAuthService

# Models for soft-delete operations
from src.infra.database.models.meal.meal import Meal
from src.infra.database.models.enums import MealStatusEnum
from src.infra.database.models.meal_planning.meal_plan import MealPlan
# TODO: Conversation table never created in database (no migration exists).
# Remove this import and related code once confirmed conversations feature is deprecated.
# from src.infra.database.models.conversation.conversation import Conversation
from src.infra.database.models.chat.thread import ChatThread
from src.infra.database.models.notification.user_fcm_token import UserFcmToken
from src.infra.database.models.notification.notification_preferences import NotificationPreferences

logger = logging.getLogger(__name__)


@handles(DeleteUserCommand)
class DeleteUserCommandHandler(EventHandler[DeleteUserCommand, Dict[str, Any]]):
    """Handler for deleting user accounts."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow
        self.firebase_auth_service = FirebaseAuthService()

    async def handle(self, command: DeleteUserCommand) -> Dict[str, Any]:
        """
        Delete user account.
        - Soft delete in database (set is_active=False)
        - Anonymize user data
        - Hard delete in Firebase Authentication
        """
        # Use provided UoW or create default
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                # Find user by firebase_uid
                user = uow.users.find_by_firebase_uid(command.firebase_uid)

                if not user or not user.is_active:
                    raise ResourceNotFoundException(
                        f"Active user with Firebase UID not found"
                    )

                # Store user_id for logging
                user_id = user.id

                # Step 1: Soft-delete all related user data
                self._soft_delete_related_data(uow, str(user_id))

                # Step 2: Anonymize user data (GDPR compliance)
                user.email = f"deleted_{user.id}@deleted.local"
                user.username = f"deleted_user_{user.id}"
                user.first_name = None
                user.last_name = None
                user.phone_number = None
                user.display_name = None
                user.photo_url = None
                user.password_hash = "DELETED"

                # Step 3: Soft delete user with timestamp
                user.is_active = False
                user.deleted_at = utc_now()
                user.last_accessed = utc_now()

                # Save changes
                uow.users.save(user)
                uow.commit()
                logger.info(f"Successfully soft deleted user in database")

                # Step 4: Revoke refresh tokens to invalidate all active sessions
                # This prevents the user from getting new access tokens
                try:
                    self.firebase_auth_service.revoke_refresh_tokens(command.firebase_uid)
                    logger.info(f"Successfully revoked Firebase refresh tokens")
                except Exception as revoke_error:
                    logger.warning(f"Token revocation failed: {str(revoke_error)}")
                    # Continue - deletion is more important

                # Step 5: Hard delete from Firebase Authentication
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
                uow.rollback()
                logger.error(f"Error deleting user account: {str(e)}")
                raise Exception(f"Failed to delete user account: {str(e)}")

    def _soft_delete_related_data(self, uow: UnitOfWorkPort, user_id: str) -> None:
        """
        Soft-delete all data related to the user.
        Uses bulk updates for performance. All operations are atomic within the transaction.
        """
        try:
            # 1. Soft-delete meals (set status=INACTIVE)
            meals_count = uow.session.query(Meal).filter(
                Meal.user_id == user_id
            ).update({Meal.status: MealStatusEnum.INACTIVE})

            # 2. Soft-delete meal_plans (set is_active=False)
            meal_plans_count = uow.session.query(MealPlan).filter(
                MealPlan.user_id == user_id
            ).update({MealPlan.is_active: False})

            # TODO: Conversation table never created - ORM model exists but no migration.
            # Causes error: "Table 'mealtrack.conversations' doesn't exist"
            # Chat functionality uses chat_threads table instead (created in migration 009).
            # Uncomment when/if conversations table is created via migration.
            # # 3. Soft-delete conversations (set is_active=False)
            # conversations_count = uow.session.query(Conversation).filter(
            #     Conversation.user_id == user_id
            # ).update({Conversation.is_active: False})

            # 3. Soft-delete chat_threads (set is_active=False)
            chat_threads_count = uow.session.query(ChatThread).filter(
                ChatThread.user_id == user_id
            ).update({ChatThread.is_active: False})

            # 4. Deactivate FCM tokens (set is_active=False)
            fcm_tokens_count = uow.session.query(UserFcmToken).filter(
                UserFcmToken.user_id == user_id
            ).update({UserFcmToken.is_active: False})

            # 5. Mark notification preferences as deleted (set is_deleted=True)
            notif_prefs_count = uow.session.query(NotificationPreferences).filter(
                NotificationPreferences.user_id == user_id
            ).update({NotificationPreferences.is_deleted: True})

            # Flush to ensure all changes are pending in the transaction
            uow.session.flush()

            logger.info(
                f"Soft-deleted related data: meals={meals_count}, meal_plans={meal_plans_count}, "
                f"chat_threads={chat_threads_count}, fcm_tokens={fcm_tokens_count}, "
                f"notification_prefs={notif_prefs_count}"
            )
        except Exception as e:
            logger.error(f"Failed to soft-delete related data: {str(e)}")
            raise
