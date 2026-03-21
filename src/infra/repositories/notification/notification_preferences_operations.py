"""Notification preferences CRUD operations."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.domain.model.notification import NotificationPreferences
from src.infra.database.models.notification import NotificationPreferences as DBNotificationPreferences

logger = logging.getLogger(__name__)


class NotificationPreferencesOperations:
    """Handles notification preferences database operations."""

    @staticmethod
    def save_notification_preferences(db: Session, preferences: NotificationPreferences) -> NotificationPreferences:
        """Save notification preferences to the database."""
        try:
            existing_prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.user_id == preferences.user_id
            ).first()

            if existing_prefs:
                existing_prefs.meal_reminders_enabled = preferences.meal_reminders_enabled
                existing_prefs.daily_summary_enabled = preferences.daily_summary_enabled
                existing_prefs.breakfast_time_minutes = preferences.breakfast_time_minutes
                existing_prefs.lunch_time_minutes = preferences.lunch_time_minutes
                existing_prefs.dinner_time_minutes = preferences.dinner_time_minutes
                existing_prefs.daily_summary_time_minutes = preferences.daily_summary_time_minutes
                existing_prefs.updated_at = preferences.updated_at
                db.commit()
                return existing_prefs.to_domain()
            else:
                db_prefs = DBNotificationPreferences(
                    id=preferences.preferences_id,
                    user_id=preferences.user_id,
                    meal_reminders_enabled=preferences.meal_reminders_enabled,
                    daily_summary_enabled=preferences.daily_summary_enabled,
                    breakfast_time_minutes=preferences.breakfast_time_minutes,
                    lunch_time_minutes=preferences.lunch_time_minutes,
                    dinner_time_minutes=preferences.dinner_time_minutes,
                    daily_summary_time_minutes=preferences.daily_summary_time_minutes,
                    created_at=preferences.created_at,
                    updated_at=preferences.updated_at
                )
                db.add(db_prefs)
                db.commit()
                return db_prefs.to_domain()
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving notification preferences: {e}")
            raise e

    @staticmethod
    def find_notification_preferences_by_user(db: Session, user_id: str) -> Optional[NotificationPreferences]:
        """Find notification preferences by user ID."""
        db_prefs = db.query(DBNotificationPreferences).filter(
            DBNotificationPreferences.user_id == user_id
        ).first()
        return db_prefs.to_domain() if db_prefs else None

    @staticmethod
    def delete_notification_preferences(db: Session, user_id: str) -> bool:
        """Delete notification preferences for a user."""
        try:
            db_prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.user_id == user_id
            ).first()

            if db_prefs:
                db.delete(db_prefs)
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting notification preferences: {e}")
            raise e
