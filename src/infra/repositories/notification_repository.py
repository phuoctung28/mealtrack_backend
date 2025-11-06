import logging
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.domain.model.notification import UserFcmToken, NotificationPreferences
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.infra.database.config import SessionLocal
from src.infra.database.models.notification import UserFcmToken as DBUserFcmToken, \
    NotificationPreferences as DBNotificationPreferences

logger = logging.getLogger(__name__)


class NotificationRepository(NotificationRepositoryPort):
    """Implementation of the notification repository using SQLAlchemy."""
    
    def __init__(self, db: Session = None):
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
    def find_users_for_meal_reminder(self, meal_type: str, time_minutes: int) -> List[str]:
        """Find user IDs who should receive meal reminders at a specific time."""
        db = self._get_db()
        
        try:
            # Determine the time field based on meal type
            if meal_type == "breakfast":
                time_field = DBNotificationPreferences.breakfast_time_minutes
            elif meal_type == "lunch":
                time_field = DBNotificationPreferences.lunch_time_minutes
            elif meal_type == "dinner":
                time_field = DBNotificationPreferences.dinner_time_minutes
            else:
                return []
            
            db_prefs = db.query(DBNotificationPreferences).filter(
                and_(
                    DBNotificationPreferences.meal_reminders_enabled == True,
                    time_field == time_minutes
                )
            ).all()
            
            return [prefs.user_id for prefs in db_prefs]
        finally:
            self._close_db_if_created(db)
    
    def find_users_for_sleep_reminder(self, time_minutes: int) -> List[str]:
        """Find user IDs who should receive sleep reminders at a specific time."""
        db = self._get_db()
        
        try:
            db_prefs = db.query(DBNotificationPreferences).filter(
                and_(
                    DBNotificationPreferences.sleep_reminders_enabled == True,
                    DBNotificationPreferences.sleep_reminder_time_minutes == time_minutes
                )
            ).all()
            
            return [prefs.user_id for prefs in db_prefs]
        finally:
            self._close_db_if_created(db)
    
    def find_users_for_water_reminder(self) -> List[str]:
        """Find user IDs who should receive water reminders."""
        db = self._get_db()
        
        try:
            db_prefs = db.query(DBNotificationPreferences).filter(
                DBNotificationPreferences.water_reminders_enabled == True
            ).all()
            
            return [prefs.user_id for prefs in db_prefs]
        finally:
            self._close_db_if_created(db)
