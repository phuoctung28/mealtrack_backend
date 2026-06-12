"""Async notification repository."""

import logging
from datetime import date

from sqlalchemy import and_, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.notification import NotificationPreferences, UserFcmToken
from src.infra.database.models.notification.notification import NotificationORM
from src.infra.database.models.notification.notification_preferences import (
    NotificationPreferencesORM,
)
from src.infra.database.models.notification.user_fcm_token import UserFcmTokenORM
from src.infra.mappers.notification_mapper import (
    fcm_token_orm_to_domain,
    notification_prefs_orm_to_domain,
)

logger = logging.getLogger(__name__)


class AsyncNotificationRepository:
    """Async notification repository. Never calls session.commit()."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # FCM Token operations
    # ------------------------------------------------------------------

    async def save_fcm_token(self, token: UserFcmToken) -> UserFcmToken:
        """Insert or update an FCM token.

        Uses PostgreSQL upsert to avoid race-condition duplicate key failures
        when multiple requests register the same token concurrently.
        """
        stmt = (
            insert(UserFcmTokenORM)
            .values(
                id=token.token_id,
                user_id=token.user_id,
                fcm_token=token.fcm_token,
                device_type=token.device_type.value,
                is_active=token.is_active,
                created_at=token.created_at,
                updated_at=token.updated_at,
            )
            .on_conflict_do_update(
                index_elements=[UserFcmTokenORM.fcm_token],
                set_={
                    "user_id": token.user_id,
                    "device_type": token.device_type.value,
                    "is_active": token.is_active,
                    "updated_at": token.updated_at,
                },
            )
            .returning(UserFcmTokenORM)
        )
        result = await self.session.execute(stmt)
        db_token = result.scalar_one()
        return fcm_token_orm_to_domain(db_token)

    async def find_fcm_token_by_token(self, fcm_token: str) -> UserFcmToken | None:
        """Find an FCM token by the token string."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(UserFcmTokenORM.fcm_token == fcm_token)
        )
        db_token = result.scalars().first()
        return fcm_token_orm_to_domain(db_token) if db_token else None

    async def find_active_fcm_tokens_by_user(self, user_id: str) -> list[UserFcmToken]:
        """Find all active FCM tokens for a user."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(
                and_(
                    UserFcmTokenORM.user_id == user_id,
                    UserFcmTokenORM.is_active == True,  # noqa: E712
                )
            )
        )
        return [fcm_token_orm_to_domain(t) for t in result.scalars().all()]

    async def deactivate_fcm_token(self, fcm_token: str) -> bool:
        """Deactivate an FCM token."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(UserFcmTokenORM.fcm_token == fcm_token)
        )
        db_token = result.scalars().first()
        if db_token:
            db_token.is_active = False
            await self.session.flush()
            return True
        return False

    async def delete_fcm_token(self, fcm_token: str) -> bool:
        """Delete an FCM token."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(UserFcmTokenORM.fcm_token == fcm_token)
        )
        db_token = result.scalars().first()
        if db_token:
            await self.session.delete(db_token)
            await self.session.flush()
            return True
        return False

    # ------------------------------------------------------------------
    # Notification Preferences operations
    # ------------------------------------------------------------------

    async def save_notification_preferences(
        self, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        """Insert or update notification preferences."""
        result = await self.session.execute(
            select(NotificationPreferencesORM).where(
                NotificationPreferencesORM.user_id == preferences.user_id
            )
        )
        existing = result.scalars().first()

        if existing:
            existing.meal_reminders_enabled = preferences.meal_reminders_enabled
            existing.daily_summary_enabled = preferences.daily_summary_enabled
            existing.breakfast_time_minutes = preferences.breakfast_time_minutes
            existing.lunch_time_minutes = preferences.lunch_time_minutes
            existing.dinner_time_minutes = preferences.dinner_time_minutes
            existing.daily_summary_time_minutes = preferences.daily_summary_time_minutes
            existing.language = preferences.language
            existing.updated_at = preferences.updated_at
            await self.session.flush()
            return notification_prefs_orm_to_domain(existing)
        else:
            db_prefs = NotificationPreferencesORM(
                id=preferences.preferences_id,
                user_id=preferences.user_id,
                meal_reminders_enabled=preferences.meal_reminders_enabled,
                daily_summary_enabled=preferences.daily_summary_enabled,
                breakfast_time_minutes=preferences.breakfast_time_minutes,
                lunch_time_minutes=preferences.lunch_time_minutes,
                dinner_time_minutes=preferences.dinner_time_minutes,
                daily_summary_time_minutes=preferences.daily_summary_time_minutes,
                language=preferences.language,
                created_at=preferences.created_at,
                updated_at=preferences.updated_at,
            )
            self.session.add(db_prefs)
            await self.session.flush()
            return notification_prefs_orm_to_domain(db_prefs)

    async def find_notification_preferences_by_user(
        self, user_id: str
    ) -> NotificationPreferences | None:
        """Find notification preferences by user ID."""
        result = await self.session.execute(
            select(NotificationPreferencesORM).where(
                NotificationPreferencesORM.user_id == user_id
            )
        )
        db_prefs = result.scalars().first()
        return notification_prefs_orm_to_domain(db_prefs) if db_prefs else None

    async def update_notification_preferences(
        self, user_id: str, preferences: NotificationPreferences
    ) -> NotificationPreferences:
        """Update notification preferences for a user (delegates to save)."""
        return await self.save_notification_preferences(preferences)

    async def update_notification_language(self, user_id: str, language: str) -> int:
        """Update the notification language for an existing preferences row."""
        result = await self.session.execute(
            update(NotificationPreferencesORM)
            .where(
                and_(
                    NotificationPreferencesORM.user_id == user_id,
                    NotificationPreferencesORM.is_deleted.is_(False),
                )
            )
            .values(language=language)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def delete_notification_preferences(self, user_id: str) -> bool:
        """Delete notification preferences for a user."""
        result = await self.session.execute(
            select(NotificationPreferencesORM).where(
                NotificationPreferencesORM.user_id == user_id
            )
        )
        db_prefs = result.scalars().first()
        if db_prefs:
            await self.session.delete(db_prefs)
            await self.session.flush()
            return True
        return False

    # ------------------------------------------------------------------
    # Notification scheduling operations
    # ------------------------------------------------------------------

    async def delete_pending_notifications_for_user(
        self, user_id: str, scheduled_date: date
    ) -> int:
        """Delete pending notifications for a user on a specific date.

        Returns the number of deleted rows.
        """
        result = await self.session.execute(
            delete(NotificationORM).where(
                and_(
                    NotificationORM.user_id == user_id,
                    NotificationORM.scheduled_date == scheduled_date,
                    NotificationORM.status == "pending",
                )
            )
        )
        await self.session.flush()
        return result.rowcount
