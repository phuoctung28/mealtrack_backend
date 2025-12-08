import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.domain.model.notification import UserFcmToken, NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.services.timezone_utils import (
    utc_to_local_minutes,
    is_in_quiet_hours,
    DEFAULT_TIMEZONE
)
from src.infra.database.config import SessionLocal
from src.infra.database.models.notification import UserFcmToken as DBUserFcmToken, \
    NotificationPreferences as DBNotificationPreferences
from src.infra.database.models.user.user import User

logger = logging.getLogger(__name__)


class NotificationRepository(NotificationRepositoryPort):
    """Implementation of the notification repository using SQLAlchemy."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize with optional session dependency."""
        self.db = db
    
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
            # Check if token already exists
            existing_token = db.query(DBUserFcmToken).filter(
                DBUserFcmToken.fcm_token == token.fcm_token
            ).first()
            
            if existing_token:
                # Update existing token
                existing_token.user_id = token.user_id
                existing_token.device_type = token.device_type.value
                existing_token.is_active = token.is_active
                existing_token.updated_at = token.updated_at
                
                db.commit()
                return existing_token.to_domain()
            else:
                # Create new token
                db_token = DBUserFcmToken(
                    id=token.token_id,
                    user_id=token.user_id,
                    fcm_token=token.fcm_token,
                    device_type=token.device_type.value,
                    is_active=token.is_active,
                    created_at=token.created_at,
                    updated_at=token.updated_at
                )
                
                db.add(db_token)
                db.commit()
                return db_token.to_domain()
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving FCM token: {e}")
            raise e
        finally:
            self._close_db_if_created(db)
    
    def find_fcm_token_by_token(self, fcm_token: str) -> Optional[UserFcmToken]:
        """Find an FCM token by the token string."""
        db = self._get_db()
        
        try:
            db_token = db.query(DBUserFcmToken).filter(
                DBUserFcmToken.fcm_token == fcm_token
            ).first()
            
            if db_token:
                return db_token.to_domain()
            else:
                return None
        finally:
            self._close_db_if_created(db)
    
    def find_active_fcm_tokens_by_user(self, user_id: str) -> List[UserFcmToken]:
        """Find all active FCM tokens for a user."""
        db = self._get_db()
        
        try:
            db_tokens = db.query(DBUserFcmToken).filter(
                and_(
                    DBUserFcmToken.user_id == user_id,
                    DBUserFcmToken.is_active == True
                )
            ).all()
            
            return [token.to_domain() for token in db_tokens]
        finally:
            self._close_db_if_created(db)
    
    def deactivate_fcm_token(self, fcm_token: str) -> bool:
        """Deactivate an FCM token."""
        db = self._get_db()
        
        try:
            db_token = db.query(DBUserFcmToken).filter(
                DBUserFcmToken.fcm_token == fcm_token
            ).first()
            
            if db_token:
                db_token.is_active = False
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deactivating FCM token: {e}")
            raise e
        finally:
            self._close_db_if_created(db)
    
    def delete_fcm_token(self, fcm_token: str) -> bool:
        """Delete an FCM token."""
        db = self._get_db()
        
        try:
            db_token = db.query(DBUserFcmToken).filter(
                DBUserFcmToken.fcm_token == fcm_token
            ).first()
            
            if db_token:
                db.delete(db_token)
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting FCM token: {e}")
            raise e
        finally:
            self._close_db_if_created(db)
    
    # Notification Preferences operations
    def save_notification_preferences(self, preferences: NotificationPreferences) -> NotificationPreferences:
        """Save notification preferences to the database."""
        db = self._get_db()
        
        try:
            # Check if preferences already exist
            existing_prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.user_id == preferences.user_id
            ).first()
            
            if existing_prefs:
                # Update existing preferences
                existing_prefs.meal_reminders_enabled = preferences.meal_reminders_enabled
                existing_prefs.water_reminders_enabled = preferences.water_reminders_enabled
                existing_prefs.sleep_reminders_enabled = preferences.sleep_reminders_enabled
                existing_prefs.progress_notifications_enabled = preferences.progress_notifications_enabled
                existing_prefs.reengagement_notifications_enabled = preferences.reengagement_notifications_enabled
                existing_prefs.breakfast_time_minutes = preferences.breakfast_time_minutes
                existing_prefs.lunch_time_minutes = preferences.lunch_time_minutes
                existing_prefs.dinner_time_minutes = preferences.dinner_time_minutes
                existing_prefs.water_reminder_interval_hours = preferences.water_reminder_interval_hours
                existing_prefs.sleep_reminder_time_minutes = preferences.sleep_reminder_time_minutes
                existing_prefs.updated_at = preferences.updated_at
                
                db.commit()
                return existing_prefs.to_domain()
            else:
                # Create new preferences
                db_prefs = DBNotificationPreferences(
                    id=preferences.preferences_id,
                    user_id=preferences.user_id,
                    meal_reminders_enabled=preferences.meal_reminders_enabled,
                    water_reminders_enabled=preferences.water_reminders_enabled,
                    sleep_reminders_enabled=preferences.sleep_reminders_enabled,
                    progress_notifications_enabled=preferences.progress_notifications_enabled,
                    reengagement_notifications_enabled=preferences.reengagement_notifications_enabled,
                    breakfast_time_minutes=preferences.breakfast_time_minutes,
                    lunch_time_minutes=preferences.lunch_time_minutes,
                    dinner_time_minutes=preferences.dinner_time_minutes,
                    water_reminder_interval_hours=preferences.water_reminder_interval_hours,
                    sleep_reminder_time_minutes=preferences.sleep_reminder_time_minutes,
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
        finally:
            self._close_db_if_created(db)
    
    def find_notification_preferences_by_user(self, user_id: str) -> Optional[NotificationPreferences]:
        """Find notification preferences by user ID."""
        db = self._get_db()
        
        try:
            db_prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.user_id == user_id
            ).first()
            
            if db_prefs:
                return db_prefs.to_domain()
            else:
                return None
        finally:
            self._close_db_if_created(db)
    
    def update_notification_preferences(self, user_id: str, preferences: NotificationPreferences) -> NotificationPreferences:
        """Update notification preferences for a user."""
        return self.save_notification_preferences(preferences)
    
    def delete_notification_preferences(self, user_id: str) -> bool:
        """Delete notification preferences for a user."""
        db = self._get_db()
        
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
        finally:
            self._close_db_if_created(db)
    
    # Utility operations
    def find_users_for_meal_reminder(self, meal_type: str, current_utc: datetime) -> List[str]:
        """
        Find user IDs who should receive meal reminders at current UTC time.
        
        Converts UTC to each user's local time for matching.
        
        Args:
            meal_type: breakfast, lunch, or dinner
            current_utc: Current UTC datetime
            
        Returns:
            List of user IDs who should receive reminder
        """
        db = self._get_db()
        
        try:
            # Determine time field based on meal type
            if meal_type == "breakfast":
                time_field = DBNotificationPreferences.breakfast_time_minutes
            elif meal_type == "lunch":
                time_field = DBNotificationPreferences.lunch_time_minutes
            elif meal_type == "dinner":
                time_field = DBNotificationPreferences.dinner_time_minutes
            else:
                return []
            
            # Query users with meal reminders enabled
            results = (
                db.query(DBNotificationPreferences.user_id, User.timezone)
                .join(User, DBNotificationPreferences.user_id == User.id)
                .filter(
                    DBNotificationPreferences.meal_reminders_enabled == True,
                    time_field.isnot(None)
                )
                .all()
            )
            
            # Filter by local time match
            matching_users = []
            for user_id, timezone in results:
                user_timezone = timezone or DEFAULT_TIMEZONE
                local_minutes = utc_to_local_minutes(current_utc, user_timezone)
                
                # Get user's preferred time
                prefs = db.query(DBNotificationPreferences).filter(
                    DBNotificationPreferences.user_id == user_id
                ).first()
                
                if prefs:
                    pref_minutes = getattr(prefs, f"{meal_type}_time_minutes")
                    if pref_minutes is not None and pref_minutes == local_minutes:
                        matching_users.append(user_id)
            
            return matching_users
            
        finally:
            self._close_db_if_created(db)
    
    def find_users_for_sleep_reminder(self, current_utc: datetime) -> List[str]:
        """
        Find user IDs who should receive sleep reminders at current UTC time.
        
        Args:
            current_utc: Current UTC datetime
            
        Returns:
            List of user IDs who should receive reminder
        """
        db = self._get_db()
        
        try:
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
            
        finally:
            self._close_db_if_created(db)
    
    def find_users_for_water_reminder(self, current_utc: datetime) -> List[str]:
        """
        Find users who should receive water reminders based on interval and quiet hours.

        Skips users whose local time is in quiet hours (sleep → breakfast).

        Args:
            current_utc: Current UTC datetime

        Returns:
            List of user IDs due for water reminder
        """
        db = self._get_db()

        try:
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

                # Check quiet hours
                user_timezone = timezone or DEFAULT_TIMEZONE
                local_minutes = utc_to_local_minutes(current_utc, user_timezone)

                if is_in_quiet_hours(local_minutes, sleep_time, breakfast_time):
                    continue  # Skip - user is sleeping

                # Check interval elapsed
                if last_sent is None:
                    matching_users.append(user_id)
                else:
                    # MySQL returns naive datetimes, so compare without timezone
                    current_naive = current_utc.replace(tzinfo=None)
                    last_sent_naive = last_sent.replace(tzinfo=None) if last_sent.tzinfo else last_sent
                    hours_since_last = (current_naive - last_sent_naive).total_seconds() / 3600
                    if hours_since_last >= interval_hours:
                        matching_users.append(user_id)

            return matching_users

        finally:
            self._close_db_if_created(db)
    
    def update_last_water_reminder(self, user_id: str, sent_at: datetime) -> bool:
        """Update last water reminder timestamp for user."""
        db = self._get_db()
        try:
            prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.user_id == user_id
            ).first()
            if prefs:
                prefs.last_water_reminder_at = sent_at
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating last water reminder for {user_id}: {e}")
            raise e
        finally:
            self._close_db_if_created(db)
