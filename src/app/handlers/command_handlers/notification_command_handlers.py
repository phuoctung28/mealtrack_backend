"""
Command handlers for notification operations.
"""
import logging
from typing import Any, Dict

from src.app.commands.notification import (
    RegisterFcmTokenCommand,
    DeleteFcmTokenCommand,
    UpdateNotificationPreferencesCommand
)
from src.domain.model.notification import UserFcmToken, NotificationPreferences, DeviceType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


class RegisterFcmTokenCommandHandler:
    """Handler for registering FCM tokens."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort):
        self.notification_repository = notification_repository
    
    async def handle(self, command: RegisterFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token registration."""
        try:
            # Convert device type string to enum
            device_type = DeviceType.IOS if command.device_type == 'ios' else DeviceType.ANDROID
            
            # Create domain model
            fcm_token = UserFcmToken.create_new(
                user_id=command.user_id,
                fcm_token=command.fcm_token,
                device_type=device_type
            )
            
            # Save to repository
            saved_token = self.notification_repository.save_fcm_token(fcm_token)
            
            logger.info(f"FCM token registered for user {command.user_id}")
            
            return {
                "success": True,
                "message": "Token registered successfully",
                "token_id": saved_token.token_id
            }
        except Exception as e:
            logger.error(f"Error registering FCM token: {e}")
            raise e


class DeleteFcmTokenCommandHandler:
    """Handler for deleting FCM tokens."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort):
        self.notification_repository = notification_repository
    
    async def handle(self, command: DeleteFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token deletion."""
        try:
            # Check if token exists and belongs to user
            existing_token = self.notification_repository.find_fcm_token_by_token(command.fcm_token)
            
            if not existing_token:
                return {
                    "success": False,
                    "message": "Token not found"
                }
            
            if existing_token.user_id != command.user_id:
                return {
                    "success": False,
                    "message": "Token does not belong to user"
                }
            
            # Delete token
            deleted = self.notification_repository.delete_fcm_token(command.fcm_token)
            
            if deleted:
                logger.info(f"FCM token deleted for user {command.user_id}")
                return {
                    "success": True,
                    "message": "Token deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to delete token"
                }
        except Exception as e:
            logger.error(f"Error deleting FCM token: {e}")
            raise e


class UpdateNotificationPreferencesCommandHandler:
    """Handler for updating notification preferences."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort):
        self.notification_repository = notification_repository
    
    async def handle(self, command: UpdateNotificationPreferencesCommand) -> Dict[str, Any]:
        """Handle notification preferences update."""
        try:
            # Get existing preferences or create default
            existing_prefs = self.notification_repository.find_notification_preferences_by_user(command.user_id)
            
            if not existing_prefs:
                # Create default preferences
                existing_prefs = NotificationPreferences.create_default(command.user_id)
                saved_prefs = self.notification_repository.save_notification_preferences(existing_prefs)
            else:
                saved_prefs = existing_prefs
            
            # Update preferences with new values
            updated_prefs = saved_prefs.update_preferences(
                meal_reminders_enabled=command.meal_reminders_enabled,
                water_reminders_enabled=command.water_reminders_enabled,
                sleep_reminders_enabled=command.sleep_reminders_enabled,
                progress_notifications_enabled=command.progress_notifications_enabled,
                reengagement_notifications_enabled=command.reengagement_notifications_enabled,
                breakfast_time_minutes=command.breakfast_time_minutes,
                lunch_time_minutes=command.lunch_time_minutes,
                dinner_time_minutes=command.dinner_time_minutes,
                water_reminder_interval_hours=command.water_reminder_interval_hours,
                sleep_reminder_time_minutes=command.sleep_reminder_time_minutes,
            )
            
            # Save updated preferences
            final_prefs = self.notification_repository.save_notification_preferences(updated_prefs)
            
            logger.info(f"Notification preferences updated for user {command.user_id}")
            
            return {
                "success": True,
                "preferences": final_prefs.to_dict()
            }
        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
            raise e
