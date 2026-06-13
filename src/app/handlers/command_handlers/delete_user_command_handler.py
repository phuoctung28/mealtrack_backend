"""
DeleteUserCommandHandler - Handler for deleting user accounts.
Performs soft delete in database and hard delete in Firebase Auth.
"""

import asyncio
import logging
from typing import Any

from src.api.dependencies.auth_cache import invalidate_cached_user_id
from src.api.exceptions import ResourceNotFoundException
from src.app.commands.user import DeleteUserCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.cache_port import CachePort
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.enums import MealStatusEnum

# Models for soft-delete operations
from src.infra.database.models.meal.meal import MealORM
from src.infra.database.models.notification.notification_preferences import (
    NotificationPreferencesORM as NotificationPreferences,
)
from src.infra.database.models.notification.user_fcm_token import (
    UserFcmTokenORM as UserFcmToken,
)
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.firebase_auth_service import FirebaseAuthService

logger = logging.getLogger(__name__)


@handles(DeleteUserCommand)
class DeleteUserCommandHandler(EventHandler[DeleteUserCommand, dict[str, Any]]):
    """Handler for deleting user accounts."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort | None = None,
        cache_service: CachePort | None = None,
    ):
        self.uow = uow
        self.cache_service = cache_service
        self.firebase_auth_service = FirebaseAuthService()

    async def handle(self, command: DeleteUserCommand) -> dict[str, Any]:
        """
        Delete user account.
        - Soft delete in database (set is_active=False)
        - Anonymize user data
        - Hard delete in Firebase Authentication
        """
        # Use provided UoW or create default
        uow = self.uow or AsyncUnitOfWork()

        async with uow:
            try:
                # Find user by firebase_uid
                user = await uow.users.find_by_firebase_uid(command.firebase_uid)

                if not user or not user.is_active:
                    raise ResourceNotFoundException(
                        "Active user with Firebase UID not found"
                    )

                # Store user_id for logging
                user_id = user.id

                # Step 1: Soft-delete all related user data
                await self._soft_delete_related_data(uow, str(user_id))

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
                await uow.users.save(user)
                await uow.commit()
                await invalidate_cached_user_id(
                    self.cache_service, command.firebase_uid
                )
                logger.info("Successfully soft deleted user in database")

                # Step 4: Revoke refresh tokens to invalidate all active sessions
                # This prevents the user from getting new access tokens
                # Run in thread pool to avoid blocking the async event loop
                tokens_revoked = False
                try:
                    await asyncio.to_thread(
                        self.firebase_auth_service.revoke_refresh_tokens,
                        command.firebase_uid,
                    )
                    tokens_revoked = True
                    logger.info("Successfully revoked Firebase refresh tokens")
                except Exception as revoke_error:
                    logger.warning(f"Token revocation failed: {str(revoke_error)}")
                    # Continue - deletion is more important

                # Step 5: Hard delete from Firebase Authentication.
                # The DB soft-delete is already committed, so a Firebase failure
                # here leaves an orphaned auth account (login still works but the
                # backend rejects it as inactive). Surface it as an alertable,
                # structured error and report it in the result so it can be
                # retried out-of-band instead of being silently dropped.
                firebase_deleted = False
                try:
                    firebase_deleted = await asyncio.to_thread(
                        self.firebase_auth_service.delete_firebase_user,
                        command.firebase_uid,
                    )
                    if firebase_deleted:
                        logger.info("Successfully deleted user from Firebase")
                    else:
                        logger.error(
                            "Firebase deletion returned False — orphaned auth account",
                            extra={
                                "firebase_uid": command.firebase_uid,
                                "user_id": str(user_id),
                                "firebase_delete_pending": True,
                            },
                        )
                except Exception as firebase_error:
                    logger.error(
                        f"Firebase deletion failed: {str(firebase_error)}",
                        exc_info=True,
                        extra={
                            "firebase_uid": command.firebase_uid,
                            "user_id": str(user_id),
                            "firebase_delete_pending": True,
                        },
                    )

                return {
                    "firebase_uid": command.firebase_uid,
                    "deleted": True,
                    "firebase_deleted": firebase_deleted,
                    "tokens_revoked": tokens_revoked,
                    "message": "Account successfully deleted",
                }

            except ResourceNotFoundException:
                # Re-raise not found errors
                raise
            except Exception as e:
                await uow.rollback()
                raise Exception(f"Failed to delete user account: {str(e)}") from e

    async def _soft_delete_related_data(self, uow, user_id: str) -> None:
        """
        Soft-delete all data related to the user.
        Uses bulk updates for performance. All operations are atomic within the transaction.
        """
        from sqlalchemy import update as sa_update

        try:
            # 1. Soft-delete meals (set status=INACTIVE)
            meals_result = await uow.session.execute(
                sa_update(MealORM)
                .where(MealORM.user_id == user_id)
                .values(status=MealStatusEnum.INACTIVE)
            )
            meals_count = meals_result.rowcount

            # 2. Soft-delete meal plans - no longer applicable (feature removed)
            meal_plans_count = 0

            # 3. Deactivate FCM tokens (set is_active=False)
            fcm_result = await uow.session.execute(
                sa_update(UserFcmToken)
                .where(UserFcmToken.user_id == user_id)
                .values(is_active=False)
            )
            fcm_tokens_count = fcm_result.rowcount

            # 4. Mark notification preferences as deleted (set is_deleted=True)
            notif_result = await uow.session.execute(
                sa_update(NotificationPreferences)
                .where(NotificationPreferences.user_id == user_id)
                .values(is_deleted=True)
            )
            notif_prefs_count = notif_result.rowcount

            # Flush to ensure all changes are pending in the transaction
            await uow.session.flush()

            logger.info(
                f"Soft-deleted related data: meals={meals_count}, meal_plans={meal_plans_count}, "
                f"fcm_tokens={fcm_tokens_count}, notification_prefs={notif_prefs_count}"
            )
        except Exception as e:
            raise
