"""
Notification preferences model for user notification settings.
"""
from sqlalchemy import Column, String, Boolean, Integer, CheckConstraint

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class NotificationPreferences(Base, BaseMixin):
    """Notification preferences table for user notification settings."""
    __tablename__ = 'notification_preferences'
    
    # User relationship (one-to-one)
    user_id = Column(String(36), nullable=False, unique=True, index=True)
    
    # Notification Type Toggles
    meal_reminders_enabled = Column(Boolean, default=True, nullable=False)
    water_reminders_enabled = Column(Boolean, default=True, nullable=False)
    sleep_reminders_enabled = Column(Boolean, default=True, nullable=False)
    progress_notifications_enabled = Column(Boolean, default=True, nullable=False)
    reengagement_notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Meal Reminder Timing (minutes from midnight: 0-1439)
    breakfast_time_minutes = Column(Integer, nullable=True)
    lunch_time_minutes = Column(Integer, nullable=True)
    dinner_time_minutes = Column(Integer, nullable=True)
    
    # Water Reminder Settings
    water_reminder_interval_hours = Column(Integer, default=2, nullable=False)
    
    # Sleep Reminder Timing (minutes from midnight)
    sleep_reminder_time_minutes = Column(Integer, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('breakfast_time_minutes >= 0 AND breakfast_time_minutes < 1440', name='check_breakfast_time'),
        CheckConstraint('lunch_time_minutes >= 0 AND lunch_time_minutes < 1440', name='check_lunch_time'),
        CheckConstraint('dinner_time_minutes >= 0 AND dinner_time_minutes < 1440', name='check_dinner_time'),
        CheckConstraint('water_reminder_interval_hours > 0', name='check_water_interval'),
        CheckConstraint('sleep_reminder_time_minutes >= 0 AND sleep_reminder_time_minutes < 1440', name='check_sleep_time'),
    )
    
    # Relationships - removed to avoid circular import issues
    
    def to_domain(self):
        """Convert database model to domain model."""
        from src.domain.model.notification import NotificationPreferences as DomainNotificationPreferences
        
        return DomainNotificationPreferences(
            preferences_id=self.id,
            user_id=self.user_id,
            meal_reminders_enabled=self.meal_reminders_enabled,
            water_reminders_enabled=self.water_reminders_enabled,
            sleep_reminders_enabled=self.sleep_reminders_enabled,
            progress_notifications_enabled=self.progress_notifications_enabled,
            reengagement_notifications_enabled=self.reengagement_notifications_enabled,
            breakfast_time_minutes=self.breakfast_time_minutes,
            lunch_time_minutes=self.lunch_time_minutes,
            dinner_time_minutes=self.dinner_time_minutes,
            water_reminder_interval_hours=self.water_reminder_interval_hours,
            sleep_reminder_time_minutes=self.sleep_reminder_time_minutes,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
