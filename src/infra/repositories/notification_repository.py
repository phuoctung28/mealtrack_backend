"""Notification repository implementation."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.model.notification import UserFcmToken, NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.infra.database.config import SessionLocal
from src.infra.repositories.notification.fcm_token_operations import FcmTokenOperations
from src.infra.repositories.notification.notification_preferences_operations import NotificationPreferencesOperations
from src.infra.repositories.notification.reminder_query_builder import ReminderQueryBuilder


class NotificationRepository(NotificationRepositoryPort):
    """Implementation of the notification repository using SQLAlchemy."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize with optional session dependency."""
        self.db = db
        self.fcm_ops = FcmTokenOperations()
        self.prefs_ops = NotificationPreferencesOperations()
        self.query_builder = ReminderQueryBuilder()

    def _get_db(self):
        """Get a database session, creating one if needed."""
        if self.db:
            return self.db
        else:
            return SessionLocal()

    def _close_db_if_created(self, db):
        """Close the database session if we created it."""
        if self.db is None and db is not None:
            db.close()

    # FCM Token operations
    def save_fcm_token(self, token: UserFcmToken) -> UserFcmToken:
        """Save an FCM token to the database."""
        db = self._get_db()
        try:
            return self.fcm_ops.save_fcm_token(db, token)
        finally:
            self._close_db_if_created(db)

    def find_fcm_token_by_token(self, fcm_token: str) -> Optional[UserFcmToken]:
        """Find an FCM token by the token string."""
        db = self._get_db()
        try:
            return self.fcm_ops.find_fcm_token_by_token(db, fcm_token)
        finally:
            self._close_db_if_created(db)

    def find_active_fcm_tokens_by_user(self, user_id: str) -> List[UserFcmToken]:
        """Find all active FCM tokens for a user."""
        db = self._get_db()
        try:
            return self.fcm_ops.find_active_fcm_tokens_by_user(db, user_id)
        finally:
            self._close_db_if_created(db)

    def deactivate_fcm_token(self, fcm_token: str) -> bool:
        """Deactivate an FCM token."""
        db = self._get_db()
        try:
            return self.fcm_ops.deactivate_fcm_token(db, fcm_token)
        finally:
            self._close_db_if_created(db)

    def delete_fcm_token(self, fcm_token: str) -> bool:
        """Delete an FCM token."""
        db = self._get_db()
        try:
            return self.fcm_ops.delete_fcm_token(db, fcm_token)
        finally:
            self._close_db_if_created(db)

    # Notification Preferences operations
    def save_notification_preferences(self, preferences: NotificationPreferences) -> NotificationPreferences:
        """Save notification preferences to the database."""
        db = self._get_db()
        try:
            return self.prefs_ops.save_notification_preferences(db, preferences)
        finally:
            self._close_db_if_created(db)

    def find_notification_preferences_by_user(self, user_id: str) -> Optional[NotificationPreferences]:
        """Find notification preferences by user ID."""
        db = self._get_db()
        try:
            return self.prefs_ops.find_notification_preferences_by_user(db, user_id)
        finally:
            self._close_db_if_created(db)

    def update_notification_preferences(self, user_id: str, preferences: NotificationPreferences) -> NotificationPreferences:
        """Update notification preferences for a user."""
        return self.save_notification_preferences(preferences)

    def delete_notification_preferences(self, user_id: str) -> bool:
        """Delete notification preferences for a user."""
        db = self._get_db()
        try:
            return self.prefs_ops.delete_notification_preferences(db, user_id)
        finally:
            self._close_db_if_created(db)

    # Utility operations
    def find_users_for_meal_reminder(self, meal_type: str, current_utc: datetime) -> List[str]:
        """Find user IDs who should receive meal reminders at current UTC time."""
        db = self._get_db()
        try:
            return self.query_builder.find_users_for_meal_reminder(db, meal_type, current_utc)
        finally:
            self._close_db_if_created(db)

    def find_users_for_sleep_reminder(self, current_utc: datetime) -> List[str]:
        """Find user IDs who should receive sleep reminders at current UTC time."""
        db = self._get_db()
        try:
            return self.query_builder.find_users_for_sleep_reminder(db, current_utc)
        finally:
            self._close_db_if_created(db)

    def find_users_for_fixed_water_reminder(self, current_utc: datetime) -> List[str]:
        """Find user IDs who should receive water reminders at their fixed time."""
        db = self._get_db()
        try:
            return self.query_builder.find_users_for_fixed_water_reminder(db, current_utc)
        finally:
            self._close_db_if_created(db)

    def find_users_for_water_reminder(self, current_utc: datetime) -> List[str]:
        """Find users who should receive water reminders based on interval and quiet hours."""
        db = self._get_db()
        try:
            return self.query_builder.find_users_for_water_reminder(db, current_utc)
        finally:
            self._close_db_if_created(db)

    def find_users_for_daily_summary(self, current_utc: datetime) -> List[str]:
        """Find user IDs who should receive daily summary at 9PM local time."""
        db = self._get_db()
        try:
            return self.query_builder.find_users_for_daily_summary(db, current_utc)
        finally:
            self._close_db_if_created(db)

    def update_last_water_reminder(self, user_id: str, sent_at: datetime) -> bool:
        """Update last water reminder timestamp for user."""
        db = self._get_db()
        try:
            return self.prefs_ops.update_last_water_reminder(db, user_id, sent_at)
        finally:
            self._close_db_if_created(db)
