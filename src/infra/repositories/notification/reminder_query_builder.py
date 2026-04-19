"""Reminder query builder for finding users due for notifications."""
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.utils.timezone_utils import (
    utc_to_local_minutes,
    DEFAULT_TIMEZONE
)
from src.infra.database.models.notification import NotificationPreferences as DBNotificationPreferences
from src.infra.database.models.notification.user_fcm_token import UserFcmToken as DBUserFcmToken
from src.infra.database.models.user.user import User


class ReminderQueryBuilder:
    """Builds queries for finding users due for reminders."""

    @staticmethod
    def _active_token_users_subquery(db: Session):
        """Subquery returning user_ids with at least one active FCM token."""
        return (
            db.query(DBUserFcmToken.user_id)
            .filter(DBUserFcmToken.is_active == True)
            .subquery()
        )

    @staticmethod
    def find_users_for_meal_reminder(db: Session, meal_type: str, current_utc: datetime) -> List[str]:
        """
        Find user IDs who should receive meal reminders at current UTC time.

        Converts UTC to each user's local time for matching.

        Args:
            db: Database session
            meal_type: breakfast, lunch, or dinner
            current_utc: Current UTC datetime

        Returns:
            List of user IDs who should receive reminder
        """
        if meal_type == "breakfast":
            time_field = DBNotificationPreferences.breakfast_time_minutes
        elif meal_type == "lunch":
            time_field = DBNotificationPreferences.lunch_time_minutes
        elif meal_type == "dinner":
            time_field = DBNotificationPreferences.dinner_time_minutes
        else:
            return []

        active_token_users = ReminderQueryBuilder._active_token_users_subquery(db)

        results = (
            db.query(
                DBNotificationPreferences.user_id,
                User.timezone,
                time_field
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(
                DBNotificationPreferences.meal_reminders_enabled == True,
                time_field.isnot(None),
                DBNotificationPreferences.user_id.in_(
                    select(active_token_users.c.user_id)
                )
            )
            .all()
        )

        matching_users = []
        for user_id, timezone, pref_minutes in results:
            user_timezone = timezone or DEFAULT_TIMEZONE
            local_minutes = utc_to_local_minutes(current_utc, user_timezone)

            if pref_minutes is not None and pref_minutes == local_minutes:
                matching_users.append(user_id)

        return matching_users

    @staticmethod
    def find_users_for_daily_summary(db: Session, current_utc: datetime) -> List[str]:
        """
        Find users who should receive daily summary at 9PM local time.

        Converts UTC to each user's local time and matches against daily_summary_time_minutes.

        Args:
            db: Database session
            current_utc: Current UTC datetime

        Returns:
            List of user IDs who should receive daily summary at their configured time
        """
        active_token_users = ReminderQueryBuilder._active_token_users_subquery(db)

        results = (
            db.query(
                DBNotificationPreferences.user_id,
                DBNotificationPreferences.daily_summary_time_minutes,
                User.timezone
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(
                DBNotificationPreferences.daily_summary_enabled == True,
                DBNotificationPreferences.user_id.in_(
                    select(active_token_users.c.user_id)
                )
            )
            .all()
        )

        matching_users = []
        for user_id, pref_minutes, timezone in results:
            user_timezone = timezone or DEFAULT_TIMEZONE
            local_minutes = utc_to_local_minutes(current_utc, user_timezone)

            # Default to 1260 (9:00 PM) if NULL
            summary_time = pref_minutes if pref_minutes is not None else 1260

            if local_minutes == summary_time:
                matching_users.append(user_id)

        return matching_users
