"""Async notification repository.

Only implements request-path methods (FCM token + preferences CRUD).
Background-task methods (find_users_for_meal_reminder,
find_users_for_daily_summary) remain on the sync NotificationRepository
and will be migrated in Phase 3b.
"""
import logging
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.model.notification import UserFcmToken, NotificationPreferences
from src.infra.database.models.notification.user_fcm_token import UserFcmTokenORM
from src.infra.database.models.notification.notification_preferences import NotificationPreferencesORM
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
        """Insert or update an FCM token."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(UserFcmTokenORM.fcm_token == token.fcm_token)
        )
        existing = result.scalars().first()

        if existing:
            existing.user_id = token.user_id
            existing.device_type = token.device_type.value
            existing.is_active = token.is_active
            existing.updated_at = token.updated_at
            await self.session.flush()
            return fcm_token_orm_to_domain(existing)
        else:
            db_token = UserFcmTokenORM(
                id=token.token_id,
                user_id=token.user_id,
                fcm_token=token.fcm_token,
                device_type=token.device_type.value,
                is_active=token.is_active,
                created_at=token.created_at,
                updated_at=token.updated_at,
            )
            self.session.add(db_token)
            await self.session.flush()
            return fcm_token_orm_to_domain(db_token)

    async def find_fcm_token_by_token(self, fcm_token: str) -> Optional[UserFcmToken]:
        """Find an FCM token by the token string."""
        result = await self.session.execute(
            select(UserFcmTokenORM).where(UserFcmTokenORM.fcm_token == fcm_token)
        )
        db_token = result.scalars().first()
        return fcm_token_orm_to_domain(db_token) if db_token else None

    async def find_active_fcm_tokens_by_user(self, user_id: str) -> List[UserFcmToken]:
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
    ) -> Optional[NotificationPreferences]:
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
