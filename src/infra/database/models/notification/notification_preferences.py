"""
Notification preferences model for user notification settings.
"""
from sqlalchemy import Column, String, Boolean, Integer, CheckConstraint

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class NotificationPreferencesORM(Base, BaseMixin):
    """Notification preferences table for user notification settings."""
    __tablename__ = 'notification_preferences'

    # User relationship (one-to-one)
    user_id = Column(String(36), nullable=False, unique=True, index=True)

    # Notification Type Toggles
    meal_reminders_enabled = Column(Boolean, default=True, nullable=False)
    daily_summary_enabled = Column(Boolean, default=True, nullable=False)

    # Meal Reminder Timing (minutes from midnight: 0-1439)
    breakfast_time_minutes = Column(Integer, nullable=True)
    lunch_time_minutes = Column(Integer, nullable=True)
    dinner_time_minutes = Column(Integer, nullable=True)

    # Daily Summary Timing (minutes from midnight)
    daily_summary_time_minutes = Column(Integer, nullable=True, default=1260)

    # Preferred notification language (ISO 639-1: 'en', 'vi')
    language = Column(String(5), default='en', nullable=False, server_default='en')

    # Soft delete flag
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint('breakfast_time_minutes >= 0 AND breakfast_time_minutes < 1440', name='check_breakfast_time'),
        CheckConstraint('lunch_time_minutes >= 0 AND lunch_time_minutes < 1440', name='check_lunch_time'),
        CheckConstraint('dinner_time_minutes >= 0 AND dinner_time_minutes < 1440', name='check_dinner_time'),
        CheckConstraint('daily_summary_time_minutes >= 0 AND daily_summary_time_minutes < 1440', name='check_daily_summary_time'),
    )
