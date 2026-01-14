"""Reminder query builder for finding users due for notifications."""
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from src.domain.services.timezone_utils import (
    utc_to_local_minutes,
    is_in_quiet_hours,
    DEFAULT_TIMEZONE
)
from src.infra.database.models.notification import NotificationPreferences as DBNotificationPreferences
from src.infra.database.models.user.user import User


class ReminderQueryBuilder:
    """Builds queries for finding users due for reminders."""

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

        results = (
            db.query(
                DBNotificationPreferences.user_id,
                User.timezone,
                time_field
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(
                DBNotificationPreferences.meal_reminders_enabled == True,
                time_field.isnot(None)
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
    def find_users_for_sleep_reminder(db: Session, current_utc: datetime) -> List[str]:
        """
        Find user IDs who should receive sleep reminders at current UTC time.

        Args:
            db: Database session
            current_utc: Current UTC datetime

        Returns:
            List of user IDs who should receive reminder
        """
        results = (
            db.query(
                DBNotificationPreferences.user_id,
                DBNotificationPreferences.sleep_reminder_time_minutes,
                User.timezone
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(
                DBNotificationPreferences.sleep_reminders_enabled == True,
                DBNotificationPreferences.sleep_reminder_time_minutes.isnot(None)
            )
            .all()
        )

        matching_users = []
        for user_id, pref_minutes, timezone in results:
            user_timezone = timezone or DEFAULT_TIMEZONE
            local_minutes = utc_to_local_minutes(current_utc, user_timezone)

            if pref_minutes == local_minutes:
                matching_users.append(user_id)

        return matching_users

    @staticmethod
    def find_users_for_fixed_water_reminder(db: Session, current_utc: datetime) -> List[str]:
        """
        Find users who should receive water reminders at their fixed reminder time.

        Converts UTC to each user's local time and matches against water_reminder_time_minutes.

        Args:
            db: Database session
            current_utc: Current UTC datetime

        Returns:
            List of user IDs who should receive reminder at their configured time
        """
        results = (
            db.query(
                DBNotificationPreferences.user_id,
                DBNotificationPreferences.water_reminder_time_minutes,
                User.timezone
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(
                DBNotificationPreferences.water_reminders_enabled == True,
                DBNotificationPreferences.water_reminder_time_minutes.isnot(None)
            )
            .all()
        )

        matching_users = []
        for user_id, pref_minutes, timezone in results:
            user_timezone = timezone or DEFAULT_TIMEZONE
            local_minutes = utc_to_local_minutes(current_utc, user_timezone)

            # Default to 960 (4:00 PM) if NULL
            target_time = pref_minutes if pref_minutes is not None else 960

            if local_minutes == target_time:
                matching_users.append(user_id)

        return matching_users

    @staticmethod
    def find_users_for_water_reminder(db: Session, current_utc: datetime) -> List[str]:
        """
        Find users who should receive water reminders based on interval and quiet hours.

        Skips users whose local time is in quiet hours (sleep → breakfast).

        Args:
            db: Database session
            current_utc: Current UTC datetime

        Returns:
            List of user IDs due for water reminder
        """
        results = (
            db.query(
                DBNotificationPreferences.user_id,
                DBNotificationPreferences.water_reminder_interval_hours,
                DBNotificationPreferences.last_water_reminder_at,
                DBNotificationPreferences.sleep_reminder_time_minutes,
                DBNotificationPreferences.breakfast_time_minutes,
                User.timezone
            )
            .join(User, DBNotificationPreferences.user_id == User.id)
            .filter(DBNotificationPreferences.water_reminders_enabled == True)
            .all()
        )

        matching_users = []
        for (user_id, interval_hours, last_sent,
             sleep_time, breakfast_time, timezone) in results:

            user_timezone = timezone or DEFAULT_TIMEZONE
            local_minutes = utc_to_local_minutes(current_utc, user_timezone)

            if is_in_quiet_hours(local_minutes, sleep_time, breakfast_time):
                continue

            if last_sent is None:
                matching_users.append(user_id)
            else:
                current_naive = current_utc.replace(tzinfo=None)
                last_sent_naive = last_sent.replace(tzinfo=None) if last_sent.tzinfo else last_sent
                hours_since_last = (current_naive - last_sent_naive).total_seconds() / 3600
                if hours_since_last >= interval_hours:
                    matching_users.append(user_id)

        return matching_users
